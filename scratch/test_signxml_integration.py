import datetime
from datetime import timezone
import signxml
from lxml import etree
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509

key = rsa.generate_private_key(65537, 2048)
cert = (
    x509.CertificateBuilder()
    .subject_name(x509.Name([]))
    .issuer_name(x509.Name([]))
    .public_key(key.public_key())
    .serial_number(1)
    .not_valid_before(datetime.datetime.now(timezone.utc))
    .not_valid_after(datetime.datetime.now(timezone.utc) + datetime.timedelta(days=1))
    .sign(key, hashes.SHA256())
)
cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
key_pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()

def create_assertion(assertion_id="_test_1"):
    raw = f'''<saml:Assertion xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" ID="{assertion_id}" Version="2.0" IssueInstant="2026-08-31T00:00:00Z">
        <saml:Issuer>https://idp.corp</saml:Issuer>
        <saml:Subject><saml:NameID>alice@corp.com</saml:NameID></saml:Subject>
        <saml:Conditions NotBefore="2026-08-31T00:00:00Z" NotOnOrAfter="2026-09-01T00:00:00Z">
            <saml:AudienceRestriction>
                <saml:Audience>https://sp.corp</saml:Audience>
            </saml:AudienceRestriction>
        </saml:Conditions>
        <saml:AttributeStatement>
            <saml:Attribute Name="email"><saml:AttributeValue>alice@corp.com</saml:AttributeValue></saml:Attribute>
            <saml:Attribute Name="groups"><saml:AttributeValue>admins</saml:AttributeValue></saml:Attribute>
        </saml:AttributeStatement>
    </saml:Assertion>'''
    doc = etree.fromstring(raw.encode("utf-8"))
    signed = signxml.XMLSigner(
        method=signxml.methods.enveloped,
        signature_algorithm="rsa-sha256",
        digest_algorithm="sha256",
        c14n_algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"
    ).sign(doc, key=key_pem, cert=cert_pem)
    return etree.tostring(signed).decode("utf-8")

xml_signed = create_assertion()
print("Signed assertion created.")

# Test verify
verifier = signxml.XMLVerifier()
res = verifier.verify(etree.fromstring(xml_signed.encode("utf-8")), x509_cert=cert_pem)
print("Verified element tag:", res.signed_xml.tag)
print("Signed ID:", res.signed_xml.attrib.get("ID"))
