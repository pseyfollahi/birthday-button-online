from py_vapid import Vapid


vapid = Vapid()
vapid.generate_keys()

print("Public key:")
print(vapid.public_key)

print("Private key:")
print(vapid.private_key)
