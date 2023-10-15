
# Home work 1

Here is a brief description of how my protocol works:

Every packet consists of 10-byte header, in which: 
- first 4 bytes represent `id` of a current packet,
- next 4 bytes represent `ack`-number
- next 1 byte is used to mark packets split into multiple parts
- last 1 byte is reserved for later use
