# cpupi
Code to view CPU/Memory usage of various computers using UV meters attached to a Raspberry Pi.

The idea is to display CPU usage and memory (both as a percentage) of a set of computers on two VU meters. Obviously only one computer's information can be displayed at a time, so an additional LCD display is used to provide more information about the computer whose details are being displayed.

## Architecture
The system uses a client/server architecture. The Raspberry Pi is be the server, and takes care of receiving information and displaying the details of the chosen clients' information. The clients connect to the server and send their system usage information to the server for display.

### Clients
Each client opens a connection to the server on startup. This connection is kept open for the duration of the client's life. Every _n_ seconds (_n_ is undetermined at the time of writing; it may be configurable), it sends details of the system usage as a simple encoded string as follows:

`%[hostname]:0_0.0_0_0_0_0`

where [hostname] defines the name of the machine sending data, and a set of underscore-delimited numbers after the colon denoting the following items:

1. Number of CPU cores (integer)
2. CPU usage (percent, float)
3. Total RAM (bytes, integer)
4. Used RAM (bytes, integer)
5. Total swap (bytes, integer)
6. Used swap (bytes, integer)

An example string might be:

`%madeleine:6_10.5_3890036736_2355015680_2147479552_1220452352`

indicating that the client's hostname is madeleine, it has 6 CPU cores, and current CPU usage is 10.5%. The client has 3.62 Gibibytes of RAM, of which 2.19 Gibibytes is currently being used. The client is using 1.14 out of 2.19 Gibibytes of swap.

The `%` symbol is simply used to indicate the start of a data string, and thus the end of a previous data string. This will allow the server to detect incomplete strings or other possible errors.

### Server
The server will accept multiple connections from different clients. It will collect status strings from those clients (see above). It will choose which client's details to show according to its configuration.