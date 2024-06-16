#!/usr/bin/env sh
BINPATH=/home/daq/eudaq_rino/bin

$BINPATH/euRun &
sleep 1
$BINPATH/euLog &
sleep 1

#$BINPATH/euCliCollector -n FERSDataCollector -t my_dc0 &

#sleep 1

$BINPATH/euCliProducer -n DRSProducer -t my_drs0 &

