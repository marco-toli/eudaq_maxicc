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

bool DRSProducerEvent2TTreeEventConverter::Converting(
    eudaq::EventSPC      d1,
    eudaq::TTreeEventSP  d2,
    eudaq::ConfigSPC     conf
) const {
    auto ev = std::dynamic_pointer_cast<const eudaq::RawEvent>(d1);
    if (!ev) {
        EUDAQ_THROW("Failed to cast event to RawEvent");
    }

    // Prepare storage for up to 16 boards, no malloc, no smart pointers
    CAEN_DGTZ_X742_EVENT_S_t unpacked_event[16] = {}; 
    int  PID[16] = {0};

    for (auto block_n : ev->GetBlockNumList()) {
        std::vector<uint8_t> block = ev->GetBlock(block_n);
        if (block.empty()) {
            EUDAQ_THROW("Empty block encountered");
        }

        int brd, iPID;
        int index = read_header(&block, &brd, &iPID);
        if (index < 0 || brd < 0 || brd >= 16) {
            EUDAQ_THROW("Invalid header read or board index");
        }
        PID[brd] = iPID;

        // Slice off the payload and unpack into our stack‐allocated struct
        std::vector<uint8_t> data(block.begin() + index, block.end());
        unpacked_event[brd] = DRSunpack_event_S(&data);

        // PID branch
        TString branchPID = TString::Format("DRS_Board%d_PID", brd);
        if (d2->GetListOfBranches()->FindObject(branchPID)) {
            d2->SetBranchAddress(branchPID, &PID[brd]);
        } else {
            d2->Branch(branchPID, &PID[brd], "PID/I")
              ->SetAddress(&PID[brd]);
        }

        // loop over groups & channels
        auto &evt = unpacked_event[brd];
        for (int g = 0; g < MAX_X742_GROUP_SIZE; ++g) {
            if (!evt.GrPresent[g]) continue;
            auto &grp = evt.DataGroup[g];

            for (int ch = 0; ch < MAX_X742_CHANNEL_SIZE; ++ch) {
                uint32_t chSize = grp.ChSize[ch];
                // pointer into fixed‐size array
                float *buf = grp.DataChannel[ch];

                if (chSize == 0) continue;
                TString branchName = 
                  TString::Format("DRS_Board%d_Group%d_Channel%d", brd, g, ch);

                if (d2->GetListOfBranches()->FindObject(branchName)) {
                    d2->SetBranchAddress(branchName, buf);
                } else {
                    // tell ROOT it's a float array of length chSize
                    d2->Branch(branchName, buf, 
                               TString::Format("data[%d]/F", chSize))
                      ->SetAddress(buf);
                }
            }
            // (If you want to store TriggerTimeTag or StartIndexCell,
            //  add branches here, e.g. grp.TriggerTimeTag, grp.StartIndexCell.)
        }
    }  // end for each block

    return true;
}
