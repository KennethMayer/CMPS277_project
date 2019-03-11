to run tests for latency in throughput, do the following:

2pc:
create one instance of shell.py with the following command
py shell.py 50006 0 0 0 1
create four instances of network_interface.py with the following commands:
py network_interface.py replica0 1
py network_interface.py replica1 1
py network_interface.py replica2 1
py network_interface.py replica3 1

pbft:
create one instance of shell.py with the following command
py shell.py 50006 1 keyfiles/private5 client0 1
create four instances of network_interface.py with the following commands:
py network_interface.py replica0 1 1 keyfiles/private1
py network_interface.py replica1 1 1 keyfiles/private2
py network_interface.py replica2 1 1 keyfiles/private3
py network_interface.py replica3 1 1 keyfiles/private4

Next, enter into shell.py prompt:
executefile tests/lat_test (latency)
executefile tests/tp_test (throughput)

the result is shown on the prompt

To test fault tolerance with pbft, create network nodes with the following command instead:
py network_interface.py [replica1-3] 1 1 keyfiles/private[2-4] 1

create the rest as before

if you made one or zero node with the command above and no more, operations should succeed, otherwise they will fail