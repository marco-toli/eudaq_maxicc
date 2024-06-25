#include "eudaq/ROOTMonitor.hh"
#include "eudaq/RawEvent.hh"

#include "FERSlib.h"
#include "FERS_EUDAQ.h"
#include "DRS_EUDAQ.h"

#include "TH1.h"
#include "TGraph2D.h"
#include "TProfile.h"

// let there be a user-defined Ex0EventDataFormat, containing e.g. three
// double-precision attributes get'ters:
//   double GetQuantityX(), double GetQuantityY(), and double GetQuantityZ()
//struct Ex0EventDataFormat {
//  Ex0EventDataFormat(const eudaq::Event&) {}
//  double GetQuantityX() const { return (double)rand()/RAND_MAX; }
//  double GetQuantityY() const { return (double)rand()/RAND_MAX; }
//  double GetQuantityZ() const { return (double)rand()/RAND_MAX; }
//};

extern struct shmseg *shmp;
extern int shmid;


class FERSROOTMonitor : public eudaq::ROOTMonitor {
public:
  FERSROOTMonitor(const std::string& name, const std::string& runcontrol):
    eudaq::ROOTMonitor(name, "FERS-DRS ROOT monitor", runcontrol){}

  void AtConfiguration() override;
  void AtEventReception(eudaq::EventSP ev) override;

  static const uint32_t m_id_factory = eudaq::cstr2hash("FERSROOTMonitor");

private:
  TH1D* m_FERS_LG_Ch_ADC[16][64];
  TH1D* m_FERS_HG_Ch_ADC[16][64];
  TH1D* m_DRS_Ch_TS0_ADC[8];
  TProfile* m_DRS_Pulse_Ch0[8];
  //TH1D* m_my_hist;
  //TGraph2D* m_my_graph;

  int brd;
  int PID; 

  int energyLG[FERSLIB_MAX_NCH];
  int energyHG[FERSLIB_MAX_NCH];
};

namespace{
  auto mon_rootmon = eudaq::Factory<eudaq::Monitor>::
    Register<FERSROOTMonitor, const std::string&, const std::string&>(FERSROOTMonitor::m_id_factory);
}

void FERSROOTMonitor::AtConfiguration(){

        shmid = shmget(SHM_KEY, sizeof(struct shmseg), 0644|IPC_CREAT);
        //shmid = shmget(SHM_KEY, sizeof(struct shmseg), 0);
        if (shmid == -1) {
                perror("Shared memory");
        }
        EUDAQ_WARN("producer constructor: shmid = "+std::to_string(shmid));

        // Attach to the segment to get a pointer to it.
        shmp = (shmseg*)shmat(shmid, NULL, 0);
        if (shmp == (void *) -1) {
                perror("Shared memory attach");
        }




  for(int i=0;i<shmp->connectedboards;i++) {
	for(int ich=0;ich<64;ich++) {
		char hname[256];
		char tname[256];
		char sname[256];
		sprintf (hname,"FERS/Board_%d_LG/ADC_Ch%d",i,ich);
		sprintf (tname,"Board %d LG_ADC_Ch%d",i,ich);
		sprintf (sname,"h_Board%d_LG_ADC_Ch%d",i,ich);
		m_FERS_LG_Ch_ADC[i][ich] =  m_monitor->Book<TH1D>(hname,tname , sname,
			"LG ADC per channel in all channels;ADC;# of evt", 4096, 0., 8192.);
		sprintf (hname,"FERS/Board_%d_HG/ADC_Ch%d",i,ich);
		sprintf (tname,"Board %d HG_ADC_Ch%d",i,ich);
		sprintf (sname,"h_Board%d_HG_ADC_Ch%d",i,ich);
		m_FERS_HG_Ch_ADC[i][ich] =  m_monitor->Book<TH1D>(hname,tname , sname,
			"HG ADC per channel;ADC;# evt", 4096, 0., 8192.);
	}
  }
  for(int i=0;i<shmp->connectedboardsDRS;i++) {
        char hname[256];
	sprintf (hname,"DRS/Board_%d/Ch0_TS0_ADC",i);
        m_DRS_Ch_TS0_ADC[i] =  m_monitor->Book<TH1D>(hname,"Ch0_TS0_ADC" ,
                "h_Ch_TS0_ADC", "ADC in TS0;ADC;# of evt", 4096, 0., 4096.);
	sprintf (hname,"DRS/Board_%d/Pulse_Ch0",i);
  	m_DRS_Pulse_Ch0[i] = m_monitor->Book<TProfile>(hname, "DRS_Pulse_Ch0",
    		"p_DRS_Pulse_Ch0", "Average Pulse Ch0;x-axis title;y-axis title", 1024, 0., 1024.);
  }
  //m_my_graph = m_monitor->Book<TGraph2D>("Channel 0/my_graph", "Example graph");
  //m_my_graph->SetTitle("A graph;x-axis title;y-axis title;z-axis title");
  //m_monitor->SetDrawOptions(m_my_graph, "colz");
}

void FERSROOTMonitor::AtEventReception(eudaq::EventSP ev){
	//if(m_en_print)
        //        ev->Print(std::cout);


	uint32_t nsub_ev = ev->GetNumSubEvent();
	for(int iev=0; iev<nsub_ev;iev++) {
		auto ev_sub = ev->GetSubEvent(iev);
		if(ev_sub->GetDescription()=="FERSProducer") { // Decode FERS
			auto block_n_list = ev_sub->GetBlockNumList();
			for(auto &block_n: block_n_list){
		                std::vector<uint8_t> block = ev_sub->GetBlock(block_n);
				int index = read_header(&block, &brd, &PID);
				std::vector<uint8_t> data(block.begin()+index, block.end());

				//std::cout<<"---7777--- block.size() = "<<block.size()<<std::endl;
				//std::cout<<"---7777--- data.size() = "<<data.size()<<std::endl;
				//std::cout<<"---7777--- brd = "<<brd<<std::endl;
				//std::cout<<"---7777--- PID = "<<PID<<std::endl;

  				SpectEvent_t EventSpect = FERSunpack_spectevent(&data);


                                for (int i=0; i<FERSLIB_MAX_NCH; i++)
                                {
                                        energyHG[i] = EventSpect.energyHG[i];
                                        energyLG[i] = EventSpect.energyLG[i];
					m_FERS_LG_Ch_ADC[brd][i]->Fill(energyLG[i]);
					m_FERS_HG_Ch_ADC[brd][i]->Fill(energyHG[i]);
					//std::cout<<"---7777--- "<<energyHG[i]<<std::endl;
                                }




			}

		}else if(ev_sub->GetDescription()=="DRSProducer"){  //Decode DRS

			auto block_n_list = ev_sub->GetBlockNumList();
			for(auto &block_n: block_n_list){
		                std::vector<uint8_t> block = ev_sub->GetBlock(block_n);
				int index = read_header(&block, &brd, &PID);
				std::vector<uint8_t> data(block.begin()+index, block.end());

				//std::cout<<"---7777--- block.size() = "<<block.size()<<std::endl;
				//std::cout<<"---7777--- data.size() = "<<data.size()<<std::endl;
				//std::cout<<"---7777--- brd = "<<brd<<std::endl;
				//std::cout<<"---7777--- PID = "<<PID<<std::endl;

				if(data.size()>0) {
  					CAEN_DGTZ_X742_EVENT_t  Event = DRSunpack_event (&data);
					//std::cout<<"---7777--- DRS unpacked "<<std::endl;
					m_DRS_Ch_TS0_ADC[brd]->Fill(Event.DataGroup[0].DataChannel[0][0]);
					//std::cout<<"---7777--- Event.DataGroup[0].ChSize[0] "<<Event.DataGroup[0].ChSize[0]<<std::endl;
					for(int its=0;its<Event.DataGroup[0].ChSize[0];its++){
						m_DRS_Pulse_Ch0[brd]->Fill(Float_t(its+0.5),Event.DataGroup[0].DataChannel[0][its]);
					}
				}
			}

		}else { // Decode Beam elements (to be included later)
		}
	}


  //auto event = std::make_shared<Ex0EventDataFormat>(*ev);
  //m_my_hist->Fill(event->GetQuantityX());
  //m_my_graph->SetPoint(m_my_graph->GetN(),
  //  event->GetQuantityX(), event->GetQuantityY(), event->GetQuantityZ());
  //m_my_prof->Fill(event->GetQuantityX(), event->GetQuantityY());


}

