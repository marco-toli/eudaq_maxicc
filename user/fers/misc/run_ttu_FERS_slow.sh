#!/usr/bin/env sh
BINPATH=/home/daq/eudaq_rino/bin

$BINPATH/euRun &
sleep 5
$BINPATH/euLog &
sleep 5

#$BINPATH/euCliMonitor -n Ex0Monitor -t my_mon0 &
#$BINPATH/euCliMonitor -n Ex0ROOTMonitor -t my_mon0 &
$BINPATH/euCliMonitor -n FERSROOTMonitor -t my_mon0 &
#$BINPATH/euCliMonitor -n FERSMonitor -t my_mon0 &
#sleep 5

$BINPATH/euCliCollector -n FERStsDataCollector -t my_dc0 &

sleep 5

$BINPATH/euCliProducer -n FERSProducer -t my_fers0 &

