
# Home work 1

Here is a brief description of how my protocol works:

Every packet consists of 10-byte header, in which: 
- first 4 bytes represent `id` of a current packet,
- next 4 bytes represent `ack` number
- last 1 byte is used to mark packets split into multiple parts:
  + if split=0, packet was not split
  + if split=1, packet is the first or anything by last in the split sequence
  + if split=2, last packet of split sequence
