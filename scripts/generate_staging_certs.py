import datetime
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

BASE_DIR = Path(__file__).resolve().parent.parent
CERTS_DIR = BASE_DIR / "docker" / "nginx" / "certs"
CERTS_DIR.mkdir(parents=True, exist_ok=True)

crt_path = CERTS_DIR / "staging.crt"
key_path = CERTS_DIR / "staging.key"

if crt_path.exists() and key_path.exists():
    print(f"Staging SSL certificates already exist in {CERTS_DIR}")
    exit(0)

print(f"Generating self-signed SSL certificates for staging in {CERTS_DIR}...")

# Generate private key
key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)

# Write private key
with open(key_path, "wb") as f:
    f.write(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ))

# Build self-signed certificate
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Karnataka"),
    x509.NameAttribute(NameOID.LOCALITY_NAME, "Bangalore"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "EazyDoc Healthcare"),
    x509.NameAttribute(NameOID.COMMON_NAME, "staging.eazydoc.internal"),
])

cert = (
    x509.CertificateBuilder()
    .subject_name(subject)
    .issuer_name(issuer)
    .public_key(key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
    .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
    .add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.DNSName("staging.eazydoc.internal"),
            x509.DNSName("staging.eazydoc.com"),
            x509.IPAddress(datetime.ip_address("127.0.0.1") if hasattr(datetime, "ip_address") else __import__("ipaddress").ip_address("127.0.0.1")),
        ]),
        critical=False,
    )
    .sign(key, hashes.SHA256(), default_backend())
)

with open(crt_path, "wb") as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))

print("Self-signed SSL certificates generated successfully:")
print(f"  Certificate: {crt_path}")
print(f"  Private Key: {key_path}")

