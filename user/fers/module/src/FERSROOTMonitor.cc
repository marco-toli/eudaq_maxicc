#include "eudaq/ROOTMonitor.hh"
#include "eudaq/RawEvent.hh"

#include "FERSlib.h"
#include "FERS_EUDAQ.h"
#include "DRS_EUDAQ.h"

#include "TH1.h"
#include "TH2.h"
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
  int brd1[16] = {1,3,5,7,9,11,13,15,33,35,37,39,41,43,45,47};
  TH1D* m_FERS_LG_Ch_ADC[16][64];
  TH1D* m_FERS_HG_Ch_ADC[16][64];
  TH1D* m_FERS_HG_Ch_ADC1[16];
  TProfile* m_DRS_Pulse_Ch[8][32];

  TH1D* m_FERS_tempFPGA;
  TH1D* m_FERS_hv_Vmon;
  TH1D* m_FERS_hv_Imon;
  TH1I* m_FERS_hv_status_on;

  TH1D* m_trgTime_diff;
  //TH1D* m_my_hist;
  //TGraph2D* m_my_graph;

  TH2D* m_DRS_FERS;


  int brd;
  int PID; 

  uint64_t trigTime[2];
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


  m_FERS_tempFPGA =  m_monitor->Book<TH1D>("Monitor/FERS_tempFPGA","FERS_tempFPGA","h_FERS_tempFPGA","FERS_tempFPGA;Board;tempFPGA [C]",16,-0.5,15.5);
  m_FERS_hv_Vmon =  m_monitor->Book<TH1D>("Monitor/FERS_hv_Vmon","FERS_hv_Vmon","h_FERS_hv_Vmon","FERS_hv_Vmon;Board;hv_Vmon [V]",16,-0.5,15.5);
  m_FERS_hv_Imon =  m_monitor->Book<TH1D>("Monitor/FERS_hv_Imon","FERS_hv_Imon","h_FERS_hv_Imon","FERS_hv_Imon;Board;hv_Imon [mA]",16,-0.5,15.5);
  m_FERS_hv_status_on =  m_monitor->Book<TH1I>("Monitor/FERS_hv_status_on","FERS_hv_status_on","h_FERS_hv_status_on","FERS_hv_status_on;Board;hv_status_on",16,-0.5,15.5);

  m_trgTime_diff = m_monitor->Book<TH1D>("Monitor/trigTime_diff_FD","trigTime_diff_FD","h_trigTime_diff_FD","time difference between FERS and DRS in ms;;time(FERS-DRS) [ms]",3,0.,1.);

  for(int ich=0;ich<16;ich++) {
		char hname[256];
		char tname[256];
		char sname[256];
		sprintf (hname,"FERS/Board_%d_HG_SiPM/ADC_Ch%02d",1,brd1[ich]);
		sprintf (tname,"Board %d HG_ADC_Ch%02d",1,brd1[ich]);
		sprintf (sname,"h_Board%d_HG_ADC_Ch%02d",1,brd1[ich]);
		m_FERS_HG_Ch_ADC1[ich] =  m_monitor->Book<TH1D>(hname,tname , sname,
			"HG ADC;ADC;# of evt", 4096, 0., 8192.);
  }

  for(int i=0;i<shmp->connectedboards;i++) {
	for(int ich=0;ich<64;ich++) {
		char hname[256];
		char tname[256];
		char sname[256];
		sprintf (hname,"FERS/Board_%02d_LG/ADC_Ch%02d",i,ich);
		sprintf (tname,"Board %02d LG_ADC_Ch%02d",i,ich);
		sprintf (sname,"h_Board%02d_LG_ADC_Ch%02d",i,ich);
		m_FERS_LG_Ch_ADC[i][ich] =  m_monitor->Book<TH1D>(hname,tname , sname,
			"LG ADC;ADC;# of evt", 4096, 0., 8192.);
		sprintf (hname,"FERS/Board_%02d_HG/ADC_Ch%02d",i,ich);
		sprintf (tname,"Board %02d HG_ADC_Ch%02d",i,ich);
		sprintf (sname,"h_Board%02d_HG_ADC_Ch%02d",i,ich);
		m_FERS_HG_Ch_ADC[i][ich] =  m_monitor->Book<TH1D>(hname,tname , sname,
			"HG ADC;ADC;# evt", 4096, 0., 8192.);
	}
  }
  for(int i=0;i<shmp->connectedboardsDRS;i++) {
        char hname[256];
	char tname[256];
	char sname[256];
	//sprintf (hname,"DRS/Board_%d/Ch0_TS0_ADC",i);
        //m_DRS_Ch_TS0_ADC[i] =  m_monitor->Book<TH1D>(hname,"Ch0_TS0_ADC" ,
        //        "h_Ch_TS0_ADC", "ADC in TS0;ADC;# of evt", 4096, 0., 4096.);
	for( int ich =0; ich < 32; ich++) {
	sprintf (hname,"DRS/Board_%d/Pulse_Ch%02d",i, ich);
	sprintf (tname,"Board %d Pulse Ch%02d",i,ich);
	sprintf (sname,"h_Board%d_Pulse_Ch%02d",i,ich);
  	m_DRS_Pulse_Ch[i][ich] = m_monitor->Book<TProfile>(hname, tname , sname, 
    		"Average Pulse ;TS;ADC", 1024, 0., 1024.);
	}
  }
  //m_my_graph = m_monitor->Book<TGraph2D>("Channel 0/my_graph", "Example graph");
  //m_my_graph->SetTitle("A graph;x-axis title;y-axis title;z-axis title");
  //m_monitor->SetDrawOptions(m_my_graph, "colz");
  m_DRS_FERS =  m_monitor->Book<TH2D>("Test/FERS_DRS_2D", "FERS_DRS_2D" ,"h_FERS_DRS_2D","Aplitude FERS vs DRS int;DRS intADC;FERS ADC", 200,0.,1000.,200,0.,8000.);
}

void FERSROOTMonitor::AtEventReception(eudaq::EventSP ev){
	//if(m_en_print)
        //        ev->Print(std::cout);

	double sigFERS=0;
	double sigDRS=0;
	double pedDRS=0;

	uint32_t nsub_ev = ev->GetNumSubEvent();
	for(int iev=0; iev<nsub_ev;iev++) {
		auto ev_sub = ev->GetSubEvent(iev);
		if(ev_sub->GetDescription()=="FERSProducer") { // Decode FERS
			trigTime[0]=ev_sub->GetTimestampBegin()/1000;
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

			        m_FERS_tempFPGA->SetBinContent(brd+1,shmp->tempFPGA[brd]);
				m_FERS_hv_Vmon->SetBinContent(brd+1,shmp->hv_Vmon[brd]);
			        m_FERS_hv_Imon->SetBinContent(brd+1,shmp->hv_Imon[brd]);
			        m_FERS_hv_status_on->SetBinContent(brd+1,shmp->hv_status_on[brd]);

                                for (int i=0; i<FERSLIB_MAX_NCH; i++)
                                {
                                        energyHG[i] = EventSpect.energyHG[i];
                                        energyLG[i] = EventSpect.energyLG[i];
					m_FERS_LG_Ch_ADC[brd][i]->Fill(energyLG[i]);
					m_FERS_HG_Ch_ADC[brd][i]->Fill(energyHG[i]);
					//std::cout<<"---7777--- "<<energyHG[i]<<std::endl;
					if(brd==2 && i==3) sigFERS=energyLG[i];
					if(brd==1) {
						for(int ik=0;ik<16;ik++){
							if(i==brd1[ik]) m_FERS_HG_Ch_ADC1[ik]->Fill(energyHG[i]);
						}
					}
                                }




			}

		}else if(ev_sub->GetDescription()=="DRSProducer"){  //Decode DRS

			trigTime[1]=ev_sub->GetTimestampBegin()/1000;
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
					//m_DRS_Ch_TS0_ADC[brd]->Fill(Event.DataGroup[0].DataChannel[0][0]);
					int hch = 0;
					for (int igr=0; igr<4;igr++){
						if (Event.GrPresent[igr]) {
							for (int ich=0; ich<8;ich++){
							hch = ich + igr*8;
								m_DRS_Pulse_Ch[brd][hch]->Reset();
								for(int its=0;its<Event.DataGroup[igr].ChSize[ich];its++){
									m_DRS_Pulse_Ch[brd][hch]->Fill(Float_t(its+0.5),Event.DataGroup[igr].DataChannel[ich][its]);
	if (brd==3&&igr==0&&ich==0)
	  if(its>=300&&its<500) sigDRS+=Event.DataGroup[igr].DataChannel[ich][its];
	if (brd==3&&igr==0&&ich==1)
	  if(its>=300&&its<500) pedDRS+=Event.DataGroup[igr].DataChannel[ich][its];
								}
							}
						}
					}
				}
			}

		}else { // Decode Beam elements (to be included later)
		}
	}
		m_trgTime_diff->SetBinContent(2,static_cast<double>(trigTime[0])-static_cast<double>(trigTime[1]));
		m_DRS_FERS->Fill((sigDRS-pedDRS+93000)/10.,sigFERS);
		//std::cout<<"---9999---"<<sigFERS<<" , "<<sigDRS-pedDRS<<" , "<<pedDRS<<" , "<<sigDRS<<std::endl;


  //auto event = std::make_shared<Ex0EventDataFormat>(*ev);
  //m_my_hist->Fill(event->GetQuantityX());
  //m_my_graph->SetPoint(m_my_graph->GetN(),
  //  event->GetQuantityX(), event->GetQuantityY(), event->GetQuantityZ());
  //m_my_prof->Fill(event->GetQuantityX(), event->GetQuantityY());


}

