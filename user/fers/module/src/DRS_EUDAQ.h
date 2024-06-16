/////////////////////////////////////////////////////////////////////
//                         2024 June 07                            //
//                   authors: Jordan Damgov                        //
//                email: Jordan.Damgov@ttu.edu                     //
//                        notes:                                   //
/////////////////////////////////////////////////////////////////////

#ifndef _DRS_EUDAQ_h
#define _DRS_EUDAQ_h

#include "CAENDigitizer.h"
#include <vector>
#include "paramparser.h"
#include <map>
// shared structure
#include "FERS_EUDAQ_shm.h"

void make_header(int board, int DataQualifier, std::vector<uint8_t> *data);
// basic types of events
void DRSpack_event(void* Event, std::vector<uint8_t> *vec);
CAEN_DGTZ_X742_EVENT_t DRSunpack_event(std::vector<uint8_t> *vec);

void FERSpack(int nbits, uint32_t input, std::vector<uint8_t> *vec);
uint16_t FERSunpack16(int index, std::vector<uint8_t> vec);
uint32_t FERSunpack32(int index, std::vector<uint8_t> vec);
uint64_t FERSunpack64(int index, std::vector<uint8_t> vec);


#endif
