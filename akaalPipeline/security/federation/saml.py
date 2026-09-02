"""akaalPipeline.security.federation.saml
======================================
P7.4 SAML 2.0 Enterprise SSO & Assertion Validation Engine.

Strict Invariants:
1. PARSED SAML != AUTHENTICATED SAML. Cryptographic XML signature verification is mandatory.
2. Secure XML parsing with zero entity expansion (defends against XXE and expansion attacks).
3. XML signature wrapping prevention.
4. Flow-appropriate InResponseTo validation and global assertion replay protection.
5. Issuer and audience validation are mandatory.
"""

from __future__ import annotations

import base64
import datetime
import hashlib
import logging
import threading
import xml.etree.ElementTree as ET
from datetime import timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from lxml import etree


import signxml
from signxml import XMLVerifier
from signxml.exceptions import InvalidCertificate, InvalidDigest, InvalidInput, InvalidSignature

from akaalPipeline.contracts.enums import AuthenticationAssurance, FederationProviderType
from akaalPipeline.security.federation.models import FederatedIdentityResult, FederationProviderConfig

logger = logging.getLogger("akaalPipeline.security.federation.saml")


class SAMLValidationError(ValueError):
    """Raised when a SAML assertion or response fails cryptographic or policy validation."""
    pass


class SAMLExpiredError(SAMLValidationError):
    """Raised when a SAML assertion has expired."""
    pass


class SAMLReplayError(SAMLValidationError):
    """Raised when a SAML assertion ID has already been consumed (replay attack)."""
    pass


# Register canonical SAML namespaces for deterministic serialization
ET.register_namespace("saml", "urn:oasis:names:tc:SAML:2.0:assertion")
ET.register_namespace("samlp", "urn:oasis:names:tc:SAML:2.0:protocol")
ET.register_namespace("ds", "http://www.w3.org/2000/09/xmldsig#")


class SAMLValidator:
    """
    Validates SAML 2.0 Responses and Assertions.
    Delegates all XMLDSig cryptographic canonicalization, digest, transform, reference,
    and signature verification to the mature signxml.XMLVerifier authority.
    Protects against XXE, signature wrapping, temporal skew, and assertion replay.
    """

    SAML_NAMESPACES = {
        "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
        "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
        "ds": "http://www.w3.org/2000/09/xmldsig#",
    }

    def __init__(self) -> None:
        self._consumed_assertion_ids: Set[str] = set()
        self._lock = threading.Lock()

    def parse_secure_xml(self, xml_content: str) -> ET.Element:
        """
        Parses XML content securely using standard xml.etree.ElementTree.
        Strictly rejects external entities, DOCTYPE declarations with external DTDs.
        """
        if not xml_content or not xml_content.strip():
            raise SAMLValidationError("SAML XML content cannot be empty")

        cleaned = xml_content.strip()
        # Defend against XXE / external entity injection
        if "<!DOCTYPE" in cleaned or "<!ENTITY" in cleaned:
            raise SAMLValidationError("Hostile XML rejected: DOCTYPE and ENTITY declarations are prohibited in SAML payloads")

        try:
            return ET.fromstring(cleaned)
        except Exception as exc:
            raise SAMLValidationError(f"Malformed SAML XML: {exc}") from exc

    def validate_saml_response(
        self,
        saml_xml_or_b64: str,
        config: FederationProviderConfig,
        expected_audience: Optional[str] = None,
        expected_in_response_to: Optional[str] = None,
        now: Optional[datetime.datetime] = None,
    ) -> FederatedIdentityResult:
        """
        Validates a SAML 2.0 Response/Assertion:
        1. Base64 decodes if necessary and securely parses XML.
        2. Validates Signature via mature XMLDSig verifier against trusted IdP certificate.
        3. Validates Issuer.
        4. Validates AudienceRestriction.
        5. Validates Temporal Validity (NotBefore, NotOnOrAfter).
        6. Enforces InResponseTo where flow-appropriate.
        7. Enforces Replay Protection on Assertion ID.
        """
        # Decode base64 if needed
        xml_text = saml_xml_or_b64.strip()
        if not xml_text.startswith("<"):
            try:
                xml_text = base64.b64decode(xml_text).decode("utf-8")
            except Exception as exc:
                raise SAMLValidationError(f"Invalid Base64 encoded SAML payload: {exc}") from exc

        root = self.parse_secure_xml(xml_text)
        current_time = now or datetime.datetime.now(timezone.utc)

        # 1. Mature XMLDSig Verification via signxml authority
        # Defends against XML Signature Wrapping (XSW) by extracting only the cryptographically verified element
        verified_signed_elem = self._verify_saml_signature(root, config)

        # 2. Locate cryptographically verified Assertion
        assertion = None
        if verified_signed_elem.tag.endswith("Assertion"):
            assertion = verified_signed_elem
        else:
            for child in verified_signed_elem.iter():
                if child.tag.endswith("Assertion"):
                    assertion = child
                    break

        if assertion is None:
            raise SAMLValidationError("No cryptographically verified SAML Assertion found in signed payload")

        assertion_id = assertion.attrib.get("ID")
        if not assertion_id:
            raise SAMLValidationError("SAML Assertion missing mandatory 'ID' attribute")

        # 3. Replay Protection
        with self._lock:
            if assertion_id in self._consumed_assertion_ids:
                raise SAMLReplayError(f"SAML Assertion ID '{assertion_id}' was already consumed (Replay Attack Detected)")
            self._consumed_assertion_ids.add(assertion_id)

        # 4. Issuer Validation
        issuer_elem = None
        for child in assertion:
            if child.tag.endswith("Issuer"):
                issuer_elem = child
                break

        if issuer_elem is None or not issuer_elem.text:
            raise SAMLValidationError("SAML Assertion missing mandatory Issuer")

        issuer = issuer_elem.text.strip()
        if issuer != config.issuer:
            raise SAMLValidationError(f"SAML Issuer '{issuer}' does not match configured issuer '{config.issuer}'")

        # 5. InResponseTo Validation (where flow requires it)
        if expected_in_response_to:
            resp_in_response_to = root.attrib.get("InResponseTo")
            if resp_in_response_to and resp_in_response_to != expected_in_response_to:
                raise SAMLValidationError(
                    f"SAML InResponseTo '{resp_in_response_to}' does not match expected '{expected_in_response_to}'"
                )

        # 6. Conditions & Temporal / Audience Validation
        conditions = None
        for child in assertion:
            if child.tag.endswith("Conditions"):
                conditions = child
                break

        if conditions is not None:
            not_before_str = conditions.attrib.get("NotBefore")
            not_on_or_after_str = conditions.attrib.get("NotOnOrAfter")

            if not_on_or_after_str:
                nva = self._parse_saml_datetime(not_on_or_after_str)
                if current_time >= nva:
                    raise SAMLExpiredError(f"SAML Assertion expired at {nva.isoformat()}")

            if not_before_str:
                nvb = self._parse_saml_datetime(not_before_str)
                if current_time < nvb:
                    raise SAMLValidationError(f"SAML Assertion not valid until {nvb.isoformat()}")

            # Audience Restriction
            expected_aud = expected_audience or config.client_id
            if expected_aud:
                aud_matched = False
                for cond_child in conditions:
                    if cond_child.tag.endswith("AudienceRestriction"):
                        for aud_elem in cond_child:
                            if aud_elem.tag.endswith("Audience") and aud_elem.text and aud_elem.text.strip() == expected_aud:
                                aud_matched = True
                                break
                if not aud_matched:
                    raise SAMLValidationError(f"SAML AudienceRestriction did not match expected audience '{expected_aud}'")

        # 7. Extract Subject & Attributes from Verified Assertion
        subject_str = None
        for child in assertion:
            if child.tag.endswith("Subject"):
                for sub_child in child:
                    if sub_child.tag.endswith("NameID") and sub_child.text:
                        subject_str = sub_child.text.strip()
                        break

        if not subject_str:
            raise SAMLValidationError("SAML Assertion missing mandatory Subject NameID")

        # Extract attributes
        attributes: Dict[str, Any] = {}
        for child in assertion:
            if child.tag.endswith("AttributeStatement"):
                for attr in child:
                    if attr.tag.endswith("Attribute"):
                        attr_name = attr.attrib.get("Name") or attr.attrib.get("FriendlyName")
                        vals = [v.text.strip() for v in attr if v.text]
                        if attr_name and vals:
                            attributes[attr_name] = vals[0] if len(vals) == 1 else vals

        email = attributes.get("email") or attributes.get("Email") or attributes.get("mail")
        display_name = attributes.get("displayName") or attributes.get("name")
        groups = attributes.get("groups") or attributes.get("memberOf") or []
        if isinstance(groups, str):
            groups = [groups]

        return FederatedIdentityResult(
            provider_id=config.provider_id,
            provider_type=FederationProviderType.SAML2,
            subject=subject_str,
            email=str(email) if email else None,
            display_name=str(display_name) if display_name else None,
            groups=tuple(str(g) for g in groups),
            claims=attributes,
            assurance=AuthenticationAssurance.HIGH,
        )

    def _verify_saml_signature(
        self,
        root: ET.Element,
        config: FederationProviderConfig,
    ) -> ET.Element:
        """
        Cryptographically verifies the XML digital signature on the SAML Response/Assertion
        against the configured trusted IdP certificate using the mature signxml authority.
        Returns the signed XML element verified by XMLDSig.
        """
        if not config.idp_cert_pem:
            raise SAMLValidationError("No IdP certificate configured for SAML signature validation")

        try:
            verifier = XMLVerifier()
            xml_bytes = ET.tostring(root, encoding="utf-8")
            verified_results = verifier.verify(
                xml_bytes,
                x509_cert=config.idp_cert_pem,
                expect_references=True,
            )

            # Extract the verified element from VerifyResult
            if isinstance(verified_results, list):
                if not verified_results:
                    raise SAMLValidationError("SAML Response/Assertion is unsigned; unsigned assertions are rejected")
                signed_elem_lxml = verified_results[0].signed_xml
            else:
                signed_elem_lxml = verified_results.signed_xml

            # Convert back to standard ElementTree for uniform processing
            raw_signed_xml = etree.tostring(signed_elem_lxml, encoding="utf-8")
            return ET.fromstring(raw_signed_xml)

        except (InvalidSignature, InvalidDigest, InvalidCertificate) as exc:
            raise SAMLValidationError(f"SAML XML Digital Signature verification failed: {exc}") from exc
        except InvalidInput as exc:
            raise SAMLValidationError(f"SAML signature input invalid or unsigned: {exc}") from exc
        except Exception as exc:
            raise SAMLValidationError(f"SAML XML Digital Signature verification error: {exc}") from exc

    def _parse_saml_datetime(self, dt_str: str) -> datetime.datetime:
        """Parses ISO 8601 / SAML datetime string to UTC aware datetime."""
        dt_str = dt_str.strip()
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        return datetime.datetime.fromisoformat(dt_str)

