#include "eudaq/RawEvent.hh"
//#include "eudaq/TTreeEventConverter.hh"
#include "TTreeEventConverter.hh"
#include "CAENDigitizerType.h" 
#include "CAENDigitizer.h"
#include "FERS_Registers_5202.h"
#include "FERSlib.h"

#include "DRS_EUDAQ.h"
#include "FERS_EUDAQ.h"


class DRSProducerEvent2TTreeEventConverter : public eudaq::TTreeEventConverter {
public:
    bool Converting(eudaq::EventSPC d1, eudaq::TTreeEventSP d2, eudaq::ConfigSPC conf) const override;
    static const uint32_t m_id_factory;


};

const uint32_t DRSProducerEvent2TTreeEventConverter::m_id_factory = eudaq::cstr2hash("DRSProducer");

namespace {
    auto dummy0 = eudaq::Factory<eudaq::TTreeEventConverter>::
        Register<DRSProducerEvent2TTreeEventConverter>(DRSProducerEvent2TTreeEventConverter::m_id_factory);
}

bool DRSProducerEvent2TTreeEventConverter::Converting(eudaq::EventSPC d1, eudaq::TTreeEventSP d2, eudaq::ConfigSPC conf) const {
    auto ev = std::dynamic_pointer_cast<const eudaq::RawEvent>(d1);
    if (!ev) {
        EUDAQ_THROW("Failed to cast event to RawEvent");
    }


    int brd;
    int PID[16];
    int iPID;

    CAEN_DGTZ_X742_EVENT_t unpacked_event[16];
    auto block_n_list = ev->GetBlockNumList();
    for(auto &block_n: block_n_list){
	std::vector<uint8_t> block = ev->GetBlock(block_n);
        int index = read_header(&block, &brd, &iPID);
	PID[brd]=iPID;
	//std::cout<<"DRS Board= "<<brd<<", PID= "<<PID[brd]<<std::endl;
        std::vector<uint8_t> data(block.begin()+index, block.end());
	if(data.size()>0) {
		unpacked_event[brd]= DRSunpack_event (&data);
		CAEN_DGTZ_X742_EVENT_t* raw_event = &unpacked_event[brd];


	    	if (!raw_event) {
        		EUDAQ_THROW("Failed to retrieve raw event data");
    		}



            	TString boardPIDBranchName = TString::Format("DRS_Board%d_PID", brd);

	        if (d2->GetListOfBranches()->FindObject(boardPIDBranchName)) {
        	        d2->SetBranchAddress(boardPIDBranchName, &PID[brd]);
	        } else {
        	        d2->Branch(boardPIDBranchName, &PID[brd], "PID/I");
	        }


    		for (int group = 0; group < MAX_X742_GROUP_SIZE; ++group) {
        		if (raw_event->GrPresent[group]) {
            			const CAEN_DGTZ_X742_GROUP_t& dataGroup = raw_event->DataGroup[group];

	            		for (int channel = 0; channel < MAX_X742_CHANNEL_SIZE; ++channel) {
        	        		uint32_t chSize = dataGroup.ChSize[channel];
                			float* data = dataGroup.DataChannel[channel];

                			if (chSize > 0 && data) {
                    				TString branchName = TString::Format("DRS_Board%d_Group%d_Channel%d",brd, group, channel);

		                    		if (d2->GetListOfBranches()->FindObject(branchName)) {
        		                		d2->SetBranchAddress(branchName, data);
                		    		} else {
                        				d2->Branch(branchName, data, TString::Format("data[%d]/F", chSize));
	                    			}
        	        		}
            			}


        		}
    		}
	}
    } //end block








    return true;
}
