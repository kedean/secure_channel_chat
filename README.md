secure_channel_chat
===================
copyright 2013 Kevin Dean

Test implementation of a secure channel based chat system.

The protocol is as follows:

Client enters '/connect domain' to connect to domain.

Client and server are each prompted for a shared passphrase.

Each side picks a random 256-bit number, encrypts with the passphrase, then they trade (the server sends first)

Boths sides xor the two numbers together to create the shared key.

Four keys are created, enc_send, enc_recv, auth_send, and auth_recv, each is the hash of the shared key with a string identifying the purpose.

On the client-side, send/recv keys are swapped.

Communication begins.

For each message sent, the data is encrypted under enc_send, then the ciphertext is appended to the message number and hashed under HMAC with auth_send as the key. Both portions are sent.

For each received, the first 64 characters are called the authenticator. The remainder is combined with the message number and hashed under HMAC with auth_recv as the key.

If the authenticators match, the remaining received text is decrypted under enc_recv.

If a message is a tuple/list, it is joined using the hex byte \x02, then split by that byte on reception at the other end.

This makes \x02 unusable in communication, but as it is the ASCII start_of_text byte, this should not be a problem.
