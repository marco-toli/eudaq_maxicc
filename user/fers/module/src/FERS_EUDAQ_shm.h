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
#define MAXCHAR 27 // max size of chars in following struct. DON'T MAKE IT TOO BIG!!!
struct shmseg {
        // FERS
        int connectedboards = 0; // number of connected FERS boards
        int nchannels[MAX_NBRD];
        int handle[MAX_NBRD]; // handle is given by FERS_OpenDevice()
        char IP[MAX_NBRD][MAXCHAR]; // IP address
        char producer[MAX_NBRD][MAXCHAR]; // title of producer
        float HVbias[MAX_NBRD]; // HV bias
        char collector[MAX_NBRD][MAXCHAR]; // title of data collector
        // from methods:
        std::chrono::high_resolution_clock::time_point FERS_Aqu_start_time_us ;
	//int FERS_offset_us = 0;
	// FERS monitoring
	float tempFPGA[MAX_NBRD];
        float hv_Vmon[MAX_NBRD];
	float hv_Imon[MAX_NBRD];
	uint8_t hv_status_on[MAX_NBRD];


        // DRS
        int connectedboardsDRS = 0; // number of connected DRS boards
        std::chrono::high_resolution_clock::time_point DRS_Aqu_start_time_us ;

        // QTP
        int connectedboardsQTP = 0; // number of connected QTP boards

};

std::chrono::time_point<std::chrono::high_resolution_clock> get_midnight_today();

#endif
