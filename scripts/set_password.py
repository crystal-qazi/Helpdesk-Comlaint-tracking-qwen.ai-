from werkzeug.security import check_password_hash

hash_value = "scrypt:32768:8:1$MZVgYL2kkxDVQi31$ba3eb9bb0a52d383d84cc34838ed891e27c144494d78c82b997cc26a63ed3ae9ee7438cf71828d1ee0d30bbfcddc091e0c6b95a7a205f7f94d34fae538035b03"
password_to_test = "Azeem@123"  # or whatever password you used

if check_password_hash(hash_value, password_to_test):
    print("✅ Hash is valid and matches the password")
else:
    print("❌ Hash does not match")