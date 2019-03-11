from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256

key1 = RSA.generate(1024)
private_key1 = key1.export_key()
public_key1 = key1.publickey().export_key()

file_out = open('public1', 'wb')
file_out.write(public_key1)
file_out.close()

file_out = open('private1', 'wb')
file_out.write(private_key1)
file_out.close()

key2 = RSA.generate(1024)
private_key2 = key2.export_key()
public_key2 = key2.publickey().export_key()

file_out = open('public2', 'wb')
file_out.write(public_key2)
file_out.close()

file_out = open('private2', 'wb')
file_out.write(private_key2)
file_out.close()

key3 = RSA.generate(1024)
private_key3 = key3.export_key()
public_key3 = key3.publickey().export_key()

file_out = open('public3', 'wb')
file_out.write(public_key3)
file_out.close()

file_out = open('private3', 'wb')
file_out.write(private_key3)
file_out.close()

key4 = RSA.generate(1024)
private_key4 = key4.export_key()
public_key4 = key4.publickey().export_key()

file_out = open('public4', 'wb')
file_out.write(public_key4)
file_out.close()

file_out = open('private4', 'wb')
file_out.write(private_key4)
file_out.close()

key5 = RSA.generate(1024)
private_key5 = key5.export_key()
public_key5 = key5.publickey().export_key()

file_out = open('public5', 'wb')
file_out.write(public_key5)
file_out.close()

file_out = open('private5', 'wb')
file_out.write(private_key5)
file_out.close()