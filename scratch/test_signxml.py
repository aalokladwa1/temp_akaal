import datetime
import signxml
from lxml import etree
import defusedxml.lxml
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
    .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
    .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1))
    .sign(key, hashes.SHA256())
)
cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
key_pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()

raw_xml = '<saml:Assertion xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" ID="_123"><saml:Issuer>https://idp</saml:Issuer><saml:Subject><saml:NameID>alice@corp.com</saml:NameID></saml:Subject></saml:Assertion>'
doc = etree.fromstring(raw_xml.encode("utf-8"))
signed_doc = signxml.XMLSigner(
    method=signxml.methods.enveloped,
    signature_algorithm="rsa-sha256",
    digest_algorithm="sha256",
    c14n_algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"
).sign(doc, key=key_pem, cert=cert_pem)
signed_xml_str = etree.tostring(signed_doc).decode("utf-8")

verifier = signxml.XMLVerifier()
res = verifier.verify(signed_doc, x509_cert=cert_pem)
print("1. Valid signed:", res.signed_xml.tag)

# 2. Tampered content
tampered_xml = signed_xml_str.replace("alice@corp.com", "attacker@corp.com")
try:
    verifier.verify(etree.fromstring(tampered_xml.encode("utf-8")), x509_cert=cert_pem)
    print("Tampered passed (BAD)")
except Exception as e:
    print("2. Tampered caught:", type(e).__name__, e)

# 3. Wrong cert
wrong_key = rsa.generate_private_key(65537, 2048)
wrong_cert = (
    x509.CertificateBuilder()
    .subject_name(x509.Name([]))
    .issuer_name(x509.Name([]))
    .public_key(wrong_key.public_key())
    .serial_number(2)
    .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
    .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1))
    .sign(wrong_key, hashes.SHA256())
)
wrong_cert_pem = wrong_cert.public_bytes(serialization.Encoding.PEM).decode()
try:
    verifier.verify(signed_doc, x509_cert=wrong_cert_pem)
    print("Wrong cert passed (BAD)")
except Exception as e:
    print("3. Wrong cert caught:", type(e).__name__, e)

# 4. Signature wrapping attempt (wrapping signed assertion inside an unsigned response with another assertion)
wrapping_xml = f'''<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" ID="_resp1">
    <saml:Assertion ID="_fake"><saml:Subject><saml:NameID>fake@corp.com</saml:NameID></saml:Subject></saml:Assertion>
    <samlp:Extensions>
        {signed_xml_str}
    </samlp:Extensions>
</samlp:Response>'''
try:
    res_wrap = verifier.verify(etree.fromstring(wrapping_xml.encode("utf-8")), x509_cert=cert_pem)
    print("Wrapping verified signed element:", res_wrap.signed_xml.attrib.get("ID"))
    # Notice that res_wrap.signed_xml is specifically the element with ID="_123", NOT the fake outer assertion!
except Exception as e:
    print("4. Wrapping exception:", type(e).__name__, e)
