#!/usr/bin/env sh

killall -9 euCliProducer
killall -9 euCliCollector
killall -9 euCliMonitor
killall -9 euLog
killall -9 euRun

BINPATH=/home/maxiccdaq/DAQ/eudaq_tb2024/bin

$BINPATH/euRun &
sleep 0.3

$BINPATH/euLog &
sleep 0.3

$BINPATH/euCliMonitor -n FERSROOTMonitor -t my_mon0 &
sleep 0.3

$BINPATH/euCliCollector -n FERSDataCollector -t my_dc0 &
sleep 1

$BINPATH/euCliProducer -n FERSProducer -t my_fers0 &
sleep 1

$BINPATH/euCliProducer -n DRSProducer -t my_drs0 &

