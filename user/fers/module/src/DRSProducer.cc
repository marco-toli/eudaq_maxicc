#include "eudaq/Producer.hh"
#include "DRS_EUDAQ.h"
#include "CAENDigitizer.h"
#include "WDconfig.h"
#include <iostream>
#include <fstream>
#include <ratio>
#include <chrono>
#include <thread>
#include <random>
#ifndef _WIN32
#include <sys/file.h>
#endif






//----------DOC-MARK-----BEG*DEC-----DOC-MARK----------
class DRSProducer : public eudaq::Producer {
  public:
  DRSProducer(const std::string & name, const std::string & runcontrol);
  void DoInitialise() override;
  void DoConfigure() override;
  void DoStartRun() override;
  void DoStopRun() override;
  void DoTerminate() override;
  void DoReset() override;
  void RunLoop() override;
  void make_evtCnt_corr(std::map<int, std::deque<CAEN_DGTZ_X742_EVENT_t>>* m_conn_evque);
  CAEN_DGTZ_X742_EVENT_t* deep_copy_event(const CAEN_DGTZ_X742_EVENT_t *src) ;

  static const uint32_t m_id_factory = eudaq::cstr2hash("DRSProducer");
private:
  bool m_flag_ts;
  bool m_flag_tg;
  uint32_t m_plane_id;
  FILE* m_file_lock;
  std::chrono::milliseconds m_ms_busy;
  std::chrono::microseconds m_us_evt_length; // fake event length used in sync
  bool m_exit_of_run;

  int handle =-1;                 // Single Board handle
  int vhandle[16];		  // All Boards handles
  int PID_DRS[16];

  WaveDumpConfig_t   WDcfg;
  int V4718_PID =58232; // yes!, hardcoded ...
  int ret, NBoardsDRS =0 ;
  uint32_t AllocatedSize, BufferSize, NumEvents;
  CAEN_DGTZ_BoardInfo_t   BoardInfo;
  CAEN_DGTZ_EventInfo_t   EventInfo;
  CAEN_DGTZ_X742_EVENT_t  *Event742=NULL;  /* custom event struct with 8 bit data (only for 8 bit digitizers) */
  char *EventPtr = NULL;
  char *buffer = NULL;
  double TTimeTag_calib = 58.59125; // 58.594 MHz from CAEN manual

  std::map<int, std::deque<CAEN_DGTZ_X742_EVENT_t>> m_conn_evque;
  std::map<int, CAEN_DGTZ_X742_EVENT_t> m_conn_ev;

  struct shmseg *shmp;
  int shmid;

};
//----------DOC-MARK-----END*DEC-----DOC-MARK----------
//----------DOC-MARK-----BEG*REG-----DOC-MARK----------
namespace{
  auto dummy0 = eudaq::Factory<eudaq::Producer>::
    Register<DRSProducer, const std::string&, const std::string&>(DRSProducer::m_id_factory);
}
//----------DOC-MARK-----END*REG-----DOC-MARK----------
//----------DOC-MARK-----BEG*CON-----DOC-MARK----------
DRSProducer::DRSProducer(const std::string & name, const std::string & runcontrol)
  :eudaq::Producer(name, runcontrol), m_file_lock(0), m_exit_of_run(false){  
}
//----------DOC-MARK-----BEG*INI-----DOC-MARK----------
void DRSProducer::DoInitialise(){

  shmid = shmget(SHM_KEY, sizeof(struct shmseg), 0644|IPC_CREAT);
  if (shmid == -1) {
           perror("Shared memory");
  }
  EUDAQ_WARN("producer constructor: shmid = "+std::to_string(shmid));

  // Attach to the segment to get a pointer to it.
  shmp = (shmseg*)shmat(shmid, NULL, 0);
  if (shmp == (void *) -1) {
           perror("Shared memory attach");
  }


  auto ini = GetInitConfiguration();
  std::string lock_path = ini->Get("DRS_DEV_LOCK_PATH", "drslockfile.txt");
  m_file_lock = fopen(lock_path.c_str(), "a");
#ifndef _WIN32
  if(flock(fileno(m_file_lock), LOCK_EX|LOCK_NB)){ //fail
    EUDAQ_THROW("unable to lock the lockfile: "+lock_path );
  }
#endif

  char *s, *sep, ss[6][16];

  std::string DRS_BASE_ADDRESS = ini->Get("DRS_BASE_ADDRESS", "3210");
  // split DRS_BASE_ADDRESS into strings separated by ':'
  NBoardsDRS = 0;
  s = &DRS_BASE_ADDRESS[0];
  while(s < DRS_BASE_ADDRESS.c_str()+strlen(DRS_BASE_ADDRESS.c_str())) {
          sep = strchr(s, ':');
          if (sep == NULL) break;
          strncpy(ss[NBoardsDRS], s, sep-s);
          ss[NBoardsDRS][sep-s] = 0;
          s += sep-s+1;
          NBoardsDRS++;
          if (NBoardsDRS == 16) break;
        }
        strcpy(ss[NBoardsDRS++], s);
  EUDAQ_INFO("DRS: found "+std::to_string(NBoardsDRS)+ " addresses in fers.ini"
                );

  char BA[100];

  for( int brd = 0 ; brd<NBoardsDRS;brd++) {
          std::sprintf(BA,"%s0000", ss[brd]);
	  ret = CAEN_DGTZ_OpenDigitizer2(CAEN_DGTZ_USB_V4718, (void *)&V4718_PID, 0 , std::stoi(BA, 0, 16), &handle);
	  if (ret) {
		EUDAQ_THROW("Unable to open DRS at 0x"+std::string(ss[brd])+", ret = " + std::to_string(ret));
	  }
	  vhandle[brd]=handle;
    	  ret = CAEN_DGTZ_GetInfo(handle, &BoardInfo);
    	  if (ret) {
	  	EUDAQ_THROW("DRS: CAEN_DGTZ_GetInfo failed on board"+std::string(ss[brd]));
	  }else{
	  	EUDAQ_INFO("DRS: opened at 0x"+std::string(ss[brd])+ "0000 is model "+BoardInfo.ModelName
		+" SN "+std::to_string(BoardInfo.SerialNumber)
		+" | PCB Revision "+std::to_string(BoardInfo.PCB_Revision)
		+" | ROC FirmwareRel "+std::string(BoardInfo.ROC_FirmwareRel)
		+" | AMX FirmwareRel "+std::string(BoardInfo.AMC_FirmwareRel)
		);
		PID_DRS[brd]=BoardInfo.SerialNumber;
	  }
	  m_conn_evque[brd].clear();

  }
  //shmp->isEvtCntCorrDRSReady = false;
  shmp->connectedboardsDRS = NBoardsDRS;
  //shmp->DRS_trigC = 0;
  //shmp->DRS_trigT_last = 0;
}

//----------DOC-MARK-----BEG*CONF-----DOC-MARK----------
void DRSProducer::DoConfigure(){
  auto conf = GetConfiguration();
  conf->Print(std::cout);
  m_plane_id = conf->Get("DRS_PLANE_ID", 0);
  m_ms_busy = std::chrono::milliseconds(conf->Get("DRS_DURATION_BUSY_MS", 100));
  m_us_evt_length = std::chrono::microseconds(400); // used in sync.

  m_flag_ts = conf->Get("DRS_ENABLE_TIMESTAMP", 0);
  m_flag_tg = conf->Get("DRS_ENABLE_TRIGERNUMBER", 0);
  if(!m_flag_ts && !m_flag_tg){
    EUDAQ_WARN("Both Timestamp and TriggerNumber are disabled. Now, Timestamp is enabled by default");
    m_flag_ts = false;
    m_flag_tg = true;
  }

  FILE *f_ini;
  std::string drs_conf_filename= conf->Get("DRS_CONF_FILE","NOFILE");
  f_ini = fopen(drs_conf_filename.c_str(), "r");

  ParseConfigFile(f_ini, &WDcfg);
  fclose(f_ini);

  /* *************************************************************************************** */
  /* program the digitizer                                                                   */
  /* *************************************************************************************** */
  EUDAQ_INFO("DRS: # boards in Conf "+std::to_string(NBoardsDRS));
  for( int brd = 0 ; brd<NBoardsDRS;brd++) {

     ret = CAEN_DGTZ_GetInfo(vhandle[brd], &BoardInfo);
     ret = ProgramDigitizer(vhandle[brd], WDcfg, BoardInfo);

     if (ret) {
    	EUDAQ_THROW("DRS: ProgramDigitizer failed on board"+std::to_string(BoardInfo.SerialNumber));
     }
  }

  for( int brd = 0 ; brd<NBoardsDRS;brd++) {
     uint32_t status = 0;
     ret = CAEN_DGTZ_GetInfo(vhandle[brd], &BoardInfo);
     ret = CAEN_DGTZ_ReadRegister(vhandle[brd], 0x8104, &status);

     if (ret) {
    	EUDAQ_THROW("DRS: ProgramDigitizer-read failed on board"+std::to_string(BoardInfo.SerialNumber));
     }

  }
  //read twice (first read clears the previous status)
  for( int brd = 0 ; brd<NBoardsDRS;brd++) {
     uint32_t status = 0;
     ret = CAEN_DGTZ_GetInfo(vhandle[brd], &BoardInfo);
     ret = CAEN_DGTZ_ReadRegister(vhandle[brd], 0x8104, &status);

     if (ret) {
    	EUDAQ_THROW("DRS: ProgramDigitizer-read failed on board"+std::to_string(BoardInfo.SerialNumber));
     }

     // Load DRS factory calibration - baseline

/*
     if ((ret = CAEN_DGTZ_LoadDRS4CorrectionData(vhandle[brd], WDcfg.DRS4Frequency)) != CAEN_DGTZ_Success)
         EUDAQ_INFO("DRS: Cannot LoadDRS4CorrectionData on board "+std::to_string(brd));
     if ((ret = CAEN_DGTZ_EnableDRS4Correction(vhandle[brd])) != CAEN_DGTZ_Success)
        EUDAQ_INFO("DRS: Cannot EnableDRS4Correction on board "+std::to_string(brd));
*/

  }
  // Allocate memory for the event data and readout buffer
  for( int brd = 0 ; brd<NBoardsDRS;brd++) {
     ret = CAEN_DGTZ_GetInfo(vhandle[brd], &BoardInfo);
     ret = CAEN_DGTZ_AllocateEvent(vhandle[brd], (void**)&Event742);
     if (ret) {
    	EUDAQ_THROW("DRS: Allocate memory for the event data failed on board"+std::to_string(BoardInfo.SerialNumber));
     }
     ret = CAEN_DGTZ_MallocReadoutBuffer(handle, &buffer,&AllocatedSize); /* WARNING: This malloc must be done after the digitizer programming */
     if (ret) {
    	EUDAQ_THROW("DRS: Allocate memory for the readout buffer failed on board"+std::to_string(BoardInfo.SerialNumber));
     }else{
  	EUDAQ_INFO("DRS: ProgramDigitizer successful on board SN "+std::to_string(BoardInfo.SerialNumber));
  	EUDAQ_INFO("DRS: Allocate memory for the readout buffer "+std::to_string(AllocatedSize));
     }
  }


}
//----------DOC-MARK-----BEG*RUN-----DOC-MARK----------
void DRSProducer::DoStartRun(){
  m_exit_of_run = false;
  // here the hardware is told to startup data acquisition
  //ret = CAEN_DGTZ_SetExtTriggerInputMode(vhandle[0], CAEN_DGTZ_TRGMODE_DISABLED);
  //Sleep(5);
  std::chrono::time_point<std::chrono::high_resolution_clock> tp_start_aq = std::chrono::high_resolution_clock::now();
  shmp->DRS_Aqu_start_time_us=tp_start_aq;
  //auto tp_start_aq_duration = std::chrono::duration_cast<std::chrono::microseconds>(shmp->DRS_Aqu_start_time_us.time_since_epoch());
  //std::cout<<"---6666---  time[us] = " << tp_start_aq_duration.count() <<std::endl;

  //shmp->DRS_offset_us = 0;

  for( int brd = 0 ; brd<NBoardsDRS;brd++) {
     m_conn_evque[brd].clear();
     ret = CAEN_DGTZ_GetInfo(vhandle[brd], &BoardInfo);
     ret = CAEN_DGTZ_SWStartAcquisition(vhandle[brd]);

     //auto return_sq = std::chrono::steady_clock::now();
     //auto time_difference = std::chrono::duration_cast<std::chrono::microseconds>(return_sq - tp_start_aq);
     //std::cout<<"---6666---  time[us] = " << time_difference.count() <<" on board "<<brd<<std::endl;

     if (ret) {
    	EUDAQ_THROW("DRS: StartAcquisition failed on board"+std::to_string(BoardInfo.SerialNumber));
     }else{
  	EUDAQ_INFO("DRS: StartAcquisition successful on board SN "+std::to_string(BoardInfo.SerialNumber));
     }
  }

  //Sleep(5);
  //ret = CAEN_DGTZ_SetExtTriggerInputMode(vhandle[0], CAEN_DGTZ_TRGMODE_ACQ_AND_EXTOUT);


//CAEN_DGTZ_TRGMODE_DISABLED
//CAEN_DGTZ_TRGMODE_ACQ_ONLY
//CAEN_DGTZ_TRGMODE_ACQ_AND_EXTOUT


}
//----------DOC-MARK-----BEG*STOP-----DOC-MARK----------
void DRSProducer::DoStopRun(){
  m_exit_of_run = true;
  // here the hardware is told to stop data acquisition
  for( int brd = 0 ; brd<NBoardsDRS;brd++) {
     ret = CAEN_DGTZ_GetInfo(vhandle[brd], &BoardInfo);
     ret = CAEN_DGTZ_SWStopAcquisition(vhandle[brd]);
     if (ret) {
    	EUDAQ_THROW("DRS: StopAcquisition failed on board"+std::to_string(BoardInfo.SerialNumber));
     }else{
  	EUDAQ_INFO("DRS: StopAcquisition successful on board SN "+std::to_string(BoardInfo.SerialNumber));
     }

     m_conn_evque[brd].clear();
  }
  //shmp->DRS_offset_us = 0;

}
//----------DOC-MARK-----BEG*RST-----DOC-MARK----------
void DRSProducer::DoReset(){
  m_exit_of_run = true;
  if(m_file_lock){
#ifndef _WIN32
    flock(fileno(m_file_lock), LOCK_UN);
#endif
    fclose(m_file_lock);
    m_file_lock = 0;
  }
  m_ms_busy = std::chrono::milliseconds();
  m_exit_of_run = false;

  for( int brd = 0 ; brd<NBoardsDRS;brd++) {
     //ret = CAEN_DGTZ_GetInfo(vhandle[brd], &BoardInfo);
     ret = CAEN_DGTZ_Reset(vhandle[brd]);

     if (ret) {
    	EUDAQ_THROW("DRS: Reset failed on board"+std::to_string(BoardInfo.SerialNumber));
     }else{
  	EUDAQ_INFO("DRS: Reset on board SN "+std::to_string(BoardInfo.SerialNumber));
     }
  }

}
//----------DOC-MARK-----BEG*TER-----DOC-MARK----------
void DRSProducer::DoTerminate(){
  m_exit_of_run = true;
  if(m_file_lock){
    fclose(m_file_lock);
    m_file_lock = 0;
  }
  for( int brd = 0 ; brd<NBoardsDRS;brd++) {
     //ret = CAEN_DGTZ_GetInfo(vhandle[brd], &BoardInfo);
     ret = CAEN_DGTZ_Reset(vhandle[brd]);

     if (ret) {
    	EUDAQ_THROW("DRS: Reset failed on board"+std::to_string(BoardInfo.SerialNumber));
     }else{
  	EUDAQ_INFO("DRS: Reset on board SN "+std::to_string(BoardInfo.SerialNumber));
     }
  }
}
//----------DOC-MARK-----BEG*LOOP-----DOC-MARK----------
void DRSProducer::RunLoop(){
  auto tp_start_run = std::chrono::steady_clock::now();
  uint32_t trigger_n = 0;
  uint8_t x_pixel = 16;
  uint8_t y_pixel = 16;
  std::random_device rd;
  std::mt19937 gen(rd());
  std::uniform_int_distribution<uint32_t> position(0, x_pixel*y_pixel-1);
  std::uniform_int_distribution<uint32_t> signal(0, 255);


  while(!m_exit_of_run){
    auto tp_trigger = std::chrono::steady_clock::now();
    auto tp_end_of_busy = tp_trigger + m_ms_busy;

    //std::cout<<"---6666---  " << shmp->FERS_offset_us<<" , "<<shmp->DRS_offset_us<<std::endl;


    //for( int brd = 0 ; brd<ns;brd++) {
    //    CAEN_DGTZ_SendSWtrigger(vhandle[brd]);
    //}
    // real data
    //EUDAQ_INFO("DRS: Read data ------------------------ ");

    for( int brd = 0 ; brd<NBoardsDRS;brd++) {
       ret = CAEN_DGTZ_ReadData(vhandle[brd], CAEN_DGTZ_SLAVE_TERMINATED_READOUT_MBLT, buffer, &BufferSize);
       if (ret) {
      	EUDAQ_THROW("DRS: ReadData failed ret ="+ std::to_string(ret));
       }
       ret = CAEN_DGTZ_GetNumEvents(vhandle[brd], buffer, BufferSize, &NumEvents);
       if (ret) {
      	EUDAQ_THROW("DRS: CAEN_DGTZ_GetNumEvents failed");
       //}else{
       //	  EUDAQ_INFO("DRS: ReadData buffer size "+std::to_string(BufferSize)+" on board "+std::to_string(brd)
	//	+" NumEvents= "+std::to_string(NumEvents)
       //   );
       }
       //ret = CAEN_DGTZ_GetEventInfo(handle, buffer, BufferSize, i, &EventInfo, &EventPtr);
       for(int i = 0; i < (int)NumEvents; i++) {
          ret = CAEN_DGTZ_GetEventInfo(vhandle[brd], buffer, BufferSize, i, &EventInfo, &EventPtr);
          if (ret) {
	        EUDAQ_THROW("DRS: CAEN_DGTZ_GetEventInfo failed");
	  }
          ret = CAEN_DGTZ_DecodeEvent(vhandle[brd], EventPtr, (void**)&Event742);
          if (ret) {
	        EUDAQ_THROW("DRS: CAEN_DGTZ_DecodeEvent failed");
          //}else{
		//EUDAQ_INFO("DRS: EventInfo on Board " + std::to_string(*(Event742->DataGroup[0].ChSize)));
	//	EUDAQ_INFO("DRS: Group=0, ch=0, TS=5, ADC= " + std::to_string(Event742->DataGroup[0].DataChannel[0][5]));
	  }
          Event742->DataGroup[1].TriggerTimeTag = EventInfo.EventCounter; // A workaround ...

	  //m_conn_evque[brd].push_back(*Event742);
	  m_conn_evque[brd].push_back(*DRSProducer::deep_copy_event(Event742)); // Fix for shallow copy in CAEN DIgitizer

          std::cout<<"---6666---Evt, btd,  Event742->DataGroup[0].DataChannel[0][1] "
	  		<<i<<" , "<<brd<<" , "<<Event742->DataGroup[0].DataChannel[0][1]
	  		<<" , "<<Event742->DataGroup[1].TriggerTimeTag
	  		<<" , "<<m_conn_evque[brd].back().DataGroup[1].TriggerTimeTag
	  		<<" , "<<m_conn_evque[brd].front().DataGroup[1].TriggerTimeTag
	  		<<std::endl;

          //EUDAQ_INFO("Plot "+std::to_string(brd)
          //      +" , "+std::to_string(EventInfo.EventCounter)
          //      +" , "+std::to_string(Event742->DataGroup[0].TriggerTimeTag/TTimeTag_calib/1000./2.+ 12. * (brd))
          //      +" , " + std::to_string(Event742->DataGroup[0].DataChannel[0][1])
          //);

          //EUDAQ_INFO("DRS: EvInfo Board "+std::to_string(brd)
          //      +" EvC "+std::to_string(EventInfo.EventCounter)
          //      +" TrigT0 "+std::to_string(Event742->DataGroup[0].TriggerTimeTag)
          //      +"DRS: Group=0, ch=0, TS=1, ADC= " + std::to_string(Event742->DataGroup[0].DataChannel[0][1])
          //);
       }

    }



    uint32_t block_id = m_plane_id;

    int Nevt = 128;

    for( int brd = 0 ; brd<NBoardsDRS;brd++) {
		int qsize = m_conn_evque[brd].size();
          	//EUDAQ_INFO("Sorting: cheking size " + std::to_string(brd)
		//	+"  "+std::to_string(qsize) );
	       if( qsize < Nevt) Nevt = qsize;
    }
    //std::cout<<"---6666--- Nevt "<<Nevt <<std::endl;


    // Ready to transmit the queued events with calculate Evt# offset
    for(int ievt = 0; ievt<Nevt; ievt++) {
    	    auto ev = eudaq::Event::MakeUnique("DRSProducer");
    	    ev->SetTag("Plane ID", std::to_string(m_plane_id));


	    //if(m_flag_ts){
	    //  std::chrono::nanoseconds du_ts_beg_ns(tp_trigger - tp_start_run);
	    //  std::chrono::nanoseconds du_ts_end_ns(tp_end_of_busy - tp_start_run);
	    //  ev->SetTimestamp(du_ts_beg_ns.count(), du_ts_end_ns.count());
	    //}

            trigger_n=-1;
	    for(auto &conn_evque: m_conn_evque){
	        int trigger_n_ev = conn_evque.second.front().DataGroup[1].TriggerTimeTag ;  // DRS Ev counter is stored instead

        	if(trigger_n_ev< trigger_n||trigger_n<0)
	          trigger_n = trigger_n_ev;
	    }
	    if(m_flag_tg)
      		ev->SetTriggerN(trigger_n);

            //std::cout<<"---6666---  trigger_id = " << trigger_n <<std::endl;

            m_conn_ev.clear(); // Just in case ...

	    for(auto &conn_evque: m_conn_evque){
	    	auto &ev_front = conn_evque.second.front();
		int ibrd = conn_evque.first;
                        //std::cout<<"---1111---Evt, btd,  ev_front.DataGroup[0].DataChannel[0][1] trig "
			//<<ievt<<" , "<<ibrd<<" , "<<ev_front.DataGroup[0].DataChannel[0][1]
			//<<" , "<<ev_front.DataGroup[1].TriggerTimeTag
			//<<std::endl;

 		if((ev_front.DataGroup[1].TriggerTimeTag) == trigger_n){
      			m_conn_ev[ibrd]=ev_front;
			conn_evque.second.pop_front();

	    	}
	    }


	    if(m_conn_ev.size()!=NBoardsDRS) {
		EUDAQ_THROW("Event sorting failed with "+std::to_string(m_conn_ev.size())
			+" board's records instead of "+std::to_string(NBoardsDRS) );
	    }else{

	    	for( int brd = 0 ; brd<NBoardsDRS;brd++) {

                     if( m_flag_ts && brd==0 ){
                          auto du_ts_beg_us = std::chrono::duration_cast<std::chrono::microseconds>(shmp->DRS_Aqu_start_time_us - get_midnight_today());
			  uint64_t CTriggerTimeTag= static_cast<uint64_t>(m_conn_ev[brd].DataGroup[0].TriggerTimeTag);
                          auto tp_trigger0 = std::chrono::microseconds(static_cast<long int>(CTriggerTimeTag/TTimeTag_calib/2.));
                          du_ts_beg_us += tp_trigger0;
                          std::chrono::microseconds du_ts_end_us(du_ts_beg_us + m_us_evt_length);
                          ev->SetTimestamp(static_cast<uint64_t>(du_ts_beg_us.count()), static_cast<uint64_t>(du_ts_end_us.count()));
                          //std::cout<<"---6666--- du_ts_beg_us "<<du_ts_beg_us.count()/1000000
			  //	<<" du_ts_end_us "<<du_ts_end_us.count()/1000000
			  //	<<" TriggerTimeTag "<<m_conn_ev[brd].DataGroup[0].TriggerTimeTag
			  //	<<" DRS_trigC "<<shmp->DRS_trigC
			  //	<<" CTriggerTimeTag "<<CTriggerTimeTag
			  //	<<std::endl;
                     }

		     std::vector<uint8_t> data;
	    	     //ev->SetTriggerN(trigger_n);
		     make_header(brd, PID_DRS[brd], &data);
		     // Add data here
		     DRSpack_event(static_cast<void*>(&m_conn_ev[brd]),&data);

	    	     ev->AddBlock(m_plane_id+brd, data);
		} // loop over boards

          	//EUDAQ_INFO("Sending Ev");


	    	SendEvent(std::move(ev));
                m_conn_ev.clear();
	    } // if complete event with data from all boards


    }// loop over all collected events in the transfer


    std::this_thread::sleep_until(tp_end_of_busy);

  } // end   while(!m_exit_of_run){

}
//----------DOC-MARK-----END*IMP-----DOC-MARK----------



CAEN_DGTZ_X742_EVENT_t* DRSProducer::deep_copy_event(const CAEN_DGTZ_X742_EVENT_t *src) {
    // Allocate memory for the new event
    CAEN_DGTZ_X742_EVENT_t *copy = (CAEN_DGTZ_X742_EVENT_t*)malloc(sizeof(CAEN_DGTZ_X742_EVENT_t));
    if (copy == NULL) {
        return NULL; // Memory allocation failed
    }

    // Copy GrPresent array
    memcpy(copy->GrPresent, src->GrPresent, sizeof(src->GrPresent));

    // Loop through each group and copy the data
    for (int i = 0; i < MAX_X742_GROUP_SIZE; i++) {
        if (src->GrPresent[i]) { // If the group has data
            // Copy ChSize array
            memcpy(copy->DataGroup[i].ChSize, src->DataGroup[i].ChSize, sizeof(src->DataGroup[i].ChSize));
            
            // Copy TriggerTimeTag and StartIndexCell
            copy->DataGroup[i].TriggerTimeTag = src->DataGroup[i].TriggerTimeTag;
            copy->DataGroup[i].StartIndexCell = src->DataGroup[i].StartIndexCell;

            // Copy DataChannel pointers
            for (int j = 0; j < MAX_X742_CHANNEL_SIZE; j++) {
                if (src->DataGroup[i].ChSize[j] > 0) {
                    // Allocate memory for the channel data
                    copy->DataGroup[i].DataChannel[j] = (float*)malloc(src->DataGroup[i].ChSize[j] * sizeof(float));
                    if (copy->DataGroup[i].DataChannel[j] == NULL) {
                        // If allocation fails, free previously allocated memory
                        for (int k = 0; k < j; k++) {
                            free(copy->DataGroup[i].DataChannel[k]);
                        }
                        free(copy);
                        return NULL; // Memory allocation failed
                    }
                    // Copy the channel data
                    memcpy(copy->DataGroup[i].DataChannel[j], src->DataGroup[i].DataChannel[j], src->DataGroup[i].ChSize[j] * sizeof(float));
                } else {
                    copy->DataGroup[i].DataChannel[j] = NULL;
                }
            }
        } else {
            // If no data, set all pointers to NULL
            memset(copy->DataGroup[i].DataChannel, 0, sizeof(copy->DataGroup[i].DataChannel));
        }
    }

    return copy;
}
