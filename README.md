# cpupi
Code to view CPU/Memory usage of various computers using VU meters attached to a Raspberry Pi.

The idea is to display CPU usage and memory (both as a percentage) of a set of computers on two VU meters. Obviously only one computer's information can be displayed at a time, so an additional LCD display is used to provide more information about the computer whose details are being displayed.

## Architecture
The system uses a client/server architecture. The Raspberry Pi is be the server, and takes care of receiving information and displaying the details of the chosen clients' information. The clients connect to the server and send their system usage information to the server for display.

### Clients
Each client opens a connection to the server on startup. This connection is kept open for the duration of the client's life. Every _n_ seconds (_n_ is undetermined at the time of writing; it may be configurable), it sends details of the system usage as a simple encoded string as follows:

`%[hostname]:0_0.0_0_0_0_0`

where [hostname] defines the name of the machine sending data, and a set of underscore-delimited numbers after the colon denoting the following items:

1. Number of CPU cores (integer)
2. CPU usage (percent, float)
3. Memory usage (percent, float)
4. 1 minute load average (float)
5. 5 minute load average (float)
6. Total memory (Gibibytes, float)

_The ordering is stupid because I'm a lazy programmer._

An example string might be:

`%madeleine:6_34.7_72.2_3.14_3.28_3.6#`

indicating that the client's hostname is madeleine, it has 6 CPU cores, and current CPU usage is 34.7%. It has 3.6Gb RAM, of which 72.2% is in use. The 1 minute and 5 minute load averages are 3.14 and 3.28 respectively.

The `%` and `#` symbols are used to indicate the start and end of a data string. This will allow the server to detect incomplete strings or other possible errors.

### Server
The server will accept multiple connections from different clients. It will collect status strings from those clients (see above). It will choose which client's details to show according to its configuration, which simply holds an ordered list of preferred hosts.
