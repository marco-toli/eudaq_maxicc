/////////////////////////////////////////////////////////////////////
//                         2024 June 07                            //
//                   authors: Jordan Damgov                        //
//                email: Jordan.Damgov@ttu.edu                     //
//                        notes:                                   //
/////////////////////////////////////////////////////////////////////

#ifndef _FERS_EUDAQ_SHM_h
#define _FERS_EUDAQ_SHM_h

#include "CAENDigitizer.h"
//#include "FERSlib.h"
#define MAX_NBRD                       16
//#include <vector>
//#include "paramparser.h"
//#include <map>
// shared structure
#include <iostream>
#include <fstream>
#include<sys/ipc.h>
#include<sys/shm.h>
#include<sys/types.h>

#include <chrono>


#define SHM_KEY 0x12345
#define MAXCHAR 28 // max size of chars in following struct. DON'T MAKE IT TOO BIG!!!
struct shmseg {
        // FERS
        int connectedboards = 0; // number of connected FERS boards
        int nchannels[MAX_NBRD];
        int handle[MAX_NBRD]; // handle is given by FERS_OpenDevice()
        int AcquisitionMode[MAX_NBRD];
        //from ini file:
        char IP[MAX_NBRD][MAXCHAR]; // IP address
        char desc[MAX_NBRD][MAXCHAR]; // for example serial number
        //char location[MAX_NBRD][MAXCHAR]; // for instance "on the scope"
        char producer[MAX_NBRD][MAXCHAR]; // title of producer
        // from conf file:
        float HVbias[MAX_NBRD]; // HV bias
        char collector[MAX_NBRD][MAXCHAR]; // title of data collector
        // from methods:
        int EvCntCorrFERS[MAX_NBRD] = {-1}; // DRS correction for event Cnt missmatch
        int EvCntCorrCommonFERS= 0; // DRS correction for event Cnt missmatch
        std::chrono::high_resolution_clock::time_point FERS_Aqu_start_time_us ;
	int FERS_offset_us = 0;

        // DRS
        int connectedboardsDRS = 0; // number of connected DRS boards
        int EvCntCorrDRS[MAX_NBRD]= {-1} ; // DRS correction for event Cnt missmatch
        int EvCntCorrCommonDRS= 0; // DRS correction for event Cnt missmatch
        std::chrono::high_resolution_clock::time_point DRS_Aqu_start_time_us ;
	int DRS_offset_us = 0;

        bool isEvtCntCorrFERSReady ;
        bool isEvtCntCorrCommonFERSReady ;
        bool isEvtCntCorrDRSReady ;
        bool isEvtCntCorrCommonDRSReady ;
};

std::chrono::time_point<std::chrono::high_resolution_clock> get_midnight_today();

#endif
