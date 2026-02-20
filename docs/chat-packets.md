Intro to Chat Packets
=====================

In BPSR, packets comes as TCP and the data is encapsulated and encoded in protobuf format.

A usual packet is usually composed of

```
4 bytes = payload length
2 bytes = payload type (CALL, NOTIFY, FRAME_DOWN, etc) + leading 1 bit as compression flag

and depending on the type, the remaining bytes can be as follows

NOTIFY
8 bytes = service uuid
4 bytes = stub id (unused)
4 bytes = method id, maps to internal high level opcodes
rest of the bytes = payload data (in protobuf)
```

The protobuf schema is defined in the [proto directory](../proto).

## Difference between chat and "combat" packets

An observation I noticed is that the client communicates with a different server for chats
compared to the usual server handling logging on, combat, syncing, and etc.

## Example

Example of a chat receive packet
```
// Sender: Aisu1 (lvl 3) (sprout) #48749392
// To: Team Chat
// Text: this is a test 4

0000   00 00 00 4e 00 02 00 00 00 00 09 d4 a7 68 00 00
0010   00 00 00 00 00 01 0a 36 08 03 12 32 08 04 12 14
0020   08 d0 b6 9f 17 12 05 41 69 73 75 31 18 02 20 01
0030   28 03 40 01 18 9c e2 d6 cc 06 22 12 1a 10 74 68
0040   69 73 20 69 73 20 61 20 74 65 73 74 20 34
```

The following packet can be broken down into

```
// payload metadata
00 00 00 4e              // length = 78
00 02                    // frame type = NOTIFY
00 00 00 00 09 d4 a7 68  // service uuid
00 00 00 00              // stub id
00 00 00 01              // method id

// payload data (protobuf format)
// receive chat uses the NotifyNewestChitChatMsgs message
// NotifyNewestChitChatMsgs
0a 36

// v_request: NotifyNewestChitChatMsgsRequest
08 
03  // channel_id = Team chat
12 32 08 04

// chat_msg: ChitChatMsg
12 14

// send_char_info: BasicShowInfo
08 d0 b6 9f 17 12 
05 41 69 73 75 31  // len + name = "Aisu1"
18 02 20 01 28 
03  // level = 3
40 01 18 9c e2 d6 cc 06 22 12

// msg_info: ChatMsgInfo
1a 
10 74 68 69 73 20 69 73 20 61 20 74 65 73 74 20 34  // len + msg = "this is a test 4"
```

## Protobufs (TODO)

Receiving Text Message - `NotifyNewestChitChatMsgs`
