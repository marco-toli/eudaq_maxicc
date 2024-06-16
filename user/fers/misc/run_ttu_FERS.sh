#!/usr/bin/env sh
BINPATH=/home/daq/eudaq_rino/bin

$BINPATH/euRun &
sleep 1
$BINPATH/euLog &
sleep 1

#$BINPATH/euCliMonitor -n Ex0Monitor -t my_mon0 &
$BINPATH/euCliCollector -n FERSDataCollector -t my_dc0 &

sleep 1

$BINPATH/euCliProducer -n FERSProducer -t my_fers0 &
sleep 1

