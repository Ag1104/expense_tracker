"""
Generate VAPID keys for Web Push Notifications.
Run once and add output to your .env file.

Usage:
    python generate_vapid.py
"""
try:
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.backends import default_backend
    import base64

    # Generate EC key pair
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    public_key = private_key.public_key()

    # Serialize to raw bytes
    private_bytes = private_key.private_numbers().private_value.to_bytes(32, 'big')
    
    pub_numbers = public_key.public_numbers()
    public_bytes = (
        b'\x04' +
        pub_numbers.x.to_bytes(32, 'big') +
        pub_numbers.y.to_bytes(32, 'big')
    )

    # URL-safe base64 encode (no padding)
    private_b64 = base64.urlsafe_b64encode(private_bytes).rstrip(b'=').decode()
    public_b64 = base64.urlsafe_b64encode(public_bytes).rstrip(b'=').decode()

    print("Add these to your .env file:")
    print(f"\nVAPID_PUBLIC_KEY={public_b64}")
    print(f"VAPID_PRIVATE_KEY={private_b64}")
    print("\nAlso paste the public key in your frontend when subscribing.")

except ImportError:
    print("Install cryptography: pip install cryptography")
