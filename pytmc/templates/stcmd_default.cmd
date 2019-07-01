#!../../bin/rhel7-x86_64/{{binary_name}}

< envPaths
epicsEnvSet("IOCNAME", "{{name}}" )
epicsEnvSet("ENGINEER", "{{user}}" )
epicsEnvSet("LOCATION", "{{prefix}}" )
epicsEnvSet("IOCSH_PS1", "$(IOCNAME)> " )

cd "$(TOP)"

# Run common startup commands for linux soft IOC's
< /reg/d/iocCommon/All/pre_linux.cmd

# Register all support components
dbLoadDatabase("dbd/{{binary_name}}.dbd")
{{binary_name}}_registerRecordDeviceDriver(pdbbase)

cd "$(TOP)/db"

epicsEnvSet("MOTOR_PORT",    "{{motor_port}}")
epicsEnvSet("ASYN_PORT",     "{{asyn_port}}")
epicsEnvSet("PREFIX",        "{{prefix}}{{delim}}")
epicsEnvSet("ECM_NUMAXES",   "{{motors|length}}")
epicsEnvSet("NUMAXES",       "{{motors|length}}")

epicsEnvSet("IPADDR",        "{{plc_ip}}")
epicsEnvSet("AMSID",         "{{plc_ams_id}}")
epicsEnvSet("IPPORT",        "{{plc_ads_port}}")

adsAsynPortDriverConfigure("$(ASYN_PORT)","$(IPADDR)","$(AMSID)","$(IPPORT)", 1000, 0, 0, 50, 100, 1000, 0)
EthercatMCCreateController("$(MOTOR_PORT)", "$(ASYN_PORT)", "$(NUMAXES)", "200", "1000")

#define ASYN_TRACE_ERROR     0x0001
#define ASYN_TRACEIO_DEVICE  0x0002
#define ASYN_TRACEIO_FILTER  0x0004
#define ASYN_TRACEIO_DRIVER  0x0008
#define ASYN_TRACE_FLOW      0x0010
#define ASYN_TRACE_WARNING   0x0020
#define ASYN_TRACE_INFO      0x0040
asynSetTraceMask("$(ASYN_PORT)", -1, 0x41)

#define ASYN_TRACEIO_NODATA 0x0000
#define ASYN_TRACEIO_ASCII  0x0001
#define ASYN_TRACEIO_ESCAPE 0x0002
#define ASYN_TRACEIO_HEX    0x0004
asynSetTraceIOMask("$(ASYN_PORT)", -1, 2)

#define ASYN_TRACEINFO_TIME 0x0001
#define ASYN_TRACEINFO_PORT 0x0002
#define ASYN_TRACEINFO_SOURCE 0x0004
#define ASYN_TRACEINFO_THREAD 0x0008
asynSetTraceInfoMask("$(ASYN_PORT)", -1, 5)

#define AMPLIFIER_ON_FLAG_CREATE_AXIS  1
#define AMPLIFIER_ON_FLAG_WHEN_HOMING  2
#define AMPLIFIER_ON_FLAG_USING_CNEN   4

{% for motor in motors %}
epicsEnvSet("AXISCONFIG",      "{{motor.axisconfig}}")
epicsEnvSet("AXIS_NO",         "{{motor.axis_no}}")
epicsEnvSet("DESC",            "{{motor.desc}}")
epicsEnvSet("EGU",             "{{motor.egu}}")
epicsEnvSet("PREC",            "{{motor.prec}}")
epicsEnvSet("ECAXISFIELDINIT", "{{motor.additional_fields}}")
epicsEnvSet("AMPLIFIER_FLAGS", "{{motor.amplifier_flags}}")
epicsEnvSet("MOTOR_PREFIX",    "{{motor.name[0]}}")
epicsEnvSet("MOTOR_NAME",      "{{motor.name[1]}}")

EthercatMCCreateAxis("$(MOTOR_PORT)", "$(AXIS_NO)", "$(AMPLIFIER_FLAGS)", "$(AXISCONFIG)")
dbLoadRecords("EthercatMC.template", "PREFIX=$(MOTOR_PREFIX), MOTOR_NAME=$(MOTOR_NAME), R=$(MOTOR_NAME)-, MOTOR_PORT=$(MOTOR_PORT), ASYN_PORT=$(ASYN_PORT), AXIS_NO=$(AXIS_NO), DESC=$(DESC), PREC=$(PREC) $(ECAXISFIELDINIT)")
dbLoadRecords("EthercatMCreadback.template", "PREFIX=$(MOTOR_PREFIX), MOTOR_NAME=$(MOTOR_NAME), R=$(MOTOR_NAME)-, MOTOR_PORT=$(MOTOR_PORT), ASYN_PORT=$(ASYN_PORT), AXIS_NO=$(AXIS_NO), DESC=$(DESC), PREC=$(PREC) ")
dbLoadRecords("EthercatMCdebug.template", "PREFIX=$(MOTOR_PREFIX), MOTOR_NAME=$(MOTOR_NAME), MOTOR_PORT=$(MOTOR_PORT), AXIS_NO=$(AXIS_NO), PREC=3")

{% endfor %}
{% for db in additional_db_files %}
dbLoadRecords("db/{{ db.file }}", "{{ db.macros }}")

{% endfor %}
cd "$(TOP)"

dbLoadRecords("db/iocAdmin.db", "P={{prefix}},IOC={{prefix}}" )
dbLoadRecords("db/save_restoreStatus.db", "P={{prefix}},IOC={{name}}" )

# Setup autosave
set_savefile_path( "$(IOC_DATA)/$(IOC)/autosave" )
set_requestfile_path( "$(TOP)/autosave" )
save_restoreSet_status_prefix( "{{prefix}}:" )
save_restoreSet_IncompleteSetsOk( 1 )
save_restoreSet_DatedBackupFiles( 1 )
set_pass0_restoreFile( "$(IOC).sav" )
set_pass1_restoreFile( "$(IOC).sav" )

# Initialize the IOC and start processing records
iocInit()

# Start autosave backups
create_monitor_set( "$(IOC).req", 5, "" )

# All IOCs should dump some common info after initial startup.
< /reg/d/iocCommon/All/post_linux.cmd

