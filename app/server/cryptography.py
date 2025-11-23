from server.constant_file import secret_key
def encrypt_password(password:str):
    encrypted = "".join(chr(ord(char) ^ secret_key) for char in password)
    return encrypted

def verify_password(plain_password,hashed_password):
    try:
        encrypted_pass=encrypt_password(plain_password)

        return encrypted_pass==hashed_password
    except Exception as e:
        print(e)
        return False
    
