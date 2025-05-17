#include "eudaq/RawEvent.hh"
#include "TTreeEventConverter.hh"
#include "CAENDigitizerType.h" 
#include "CAENDigitizer.h"
#include "FERS_Registers_5202.h"
#include "FERSlib.h"

#include "DRS_EUDAQ.h"
#include "FERS_EUDAQ.h"
#include <memory> // For smart pointers

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

    int eventNumber = ev->GetEventNumber();
    int brd;
    int PID[16] = {0}; // Initialize PID array to prevent garbage values
    int iPID;

    // Use smart pointers for better memory management
    std::unique_ptr<CAEN_DGTZ_X742_EVENT_t> unpacked_event[16] = {nullptr}; 

    auto block_n_list = ev->GetBlockNumList();
    for (const auto& block_n : block_n_list) {
        std::vector<uint8_t> block = ev->GetBlock(block_n);

        // Validate block size and read_header return values
        if (block.empty()) {
            EUDAQ_THROW("Empty block encountered");
        }

        int index = read_header(&block, &brd, &iPID);
        if (index < 0 || brd < 0 || brd >= 16) { // Validate brd and index values
            EUDAQ_THROW("Invalid header read or board index");
        }

        PID[brd] = iPID;
        std::vector<uint8_t> data(block.begin() + index, block.end());

        if (!data.empty()) {
            unpacked_event[brd].reset(DRSunpack_event(&data)); // Use smart pointer
            if (!unpacked_event[brd]) {
                EUDAQ_THROW("Failed to retrieve raw event data");
            }

            TString boardPIDBranchName = TString::Format("DRS_Board%d_PID", brd);

            if (d2->GetListOfBranches()->FindObject(boardPIDBranchName)) {
                d2->SetBranchAddress(boardPIDBranchName, &PID[brd]);
            } else {
                d2->Branch(boardPIDBranchName, &PID[brd], "PID/I");
                d2->SetBranchAddress(boardPIDBranchName, &PID[brd]);
            }

            for (int group = 0; group < MAX_X742_GROUP_SIZE; ++group) {
                if (unpacked_event[brd]->GrPresent[group]) {
                    const auto& dataGroup = unpacked_event[brd]->DataGroup[group];

                    for (int channel = 0; channel < MAX_X742_CHANNEL_SIZE; ++channel) {
                        uint32_t chSize = dataGroup.ChSize[channel];
                        float* data = dataGroup.DataChannel[channel];

                        // Validate channel data size
                        if (chSize > 0 && data) {
                            TString branchName = TString::Format("DRS_Board%d_Group%d_Channel%d", brd, group, channel);

                            if (d2->GetListOfBranches()->FindObject(branchName)) {
                                d2->SetBranchAddress(branchName, data);
                            } else {
                                d2->Branch(branchName, data, TString::Format("data[%d]/F", chSize));
                                d2->SetBranchAddress(branchName, data);
                            }
                        }
                    }
                }
            }
        }
    } // end block_n_list loop

    return true;
}
