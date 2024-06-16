#!/usr/bin/env sh
BINPATH=/home/daq/eudaq_rino/bin

$BINPATH/euRun &
sleep 1
$BINPATH/euLog &
sleep 1
$BINPATH/euCliProducer -n FERSProducer -t my_fers0 &
