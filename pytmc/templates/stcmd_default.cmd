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

epicsEnvSet("ASYN_PORT",     "{{asyn_port}}")
epicsEnvSet("IPADDR",        "{{plc_ip}}")
epicsEnvSet("AMSID",         "{{plc_ams_id}}")
epicsEnvSet("IPPORT",        "{{plc_ads_port}}")

adsAsynPortDriverConfigure("$(ASYN_PORT)","$(IPADDR)","$(AMSID)","$(IPPORT)", 1000, 0, 0, 50, 100, 1000, 0)

{% if symbols.Symbol_FB_MotionStage %}
epicsEnvSet("MOTOR_PORT",    "{{motor_port}}")
epicsEnvSet("PREFIX",        "{{prefix}}{{delim}}")
epicsEnvSet("ECM_NUMAXES",   "{{symbols.Symbol_FB_MotionStage|length}}")
epicsEnvSet("NUMAXES",       "{{symbols.Symbol_FB_MotionStage|length}}")

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

{% for motor in symbols.Symbol_FB_MotionStage | sort(attribute='nc_axis.axis_number') %}
epicsEnvSet("AXIS_NO",         "{{motor.nc_axis.axis_number}}")
epicsEnvSet("MOTOR_PREFIX",    "{{motor|epics_prefix}}")
epicsEnvSet("MOTOR_NAME",      "{{motor|epics_suffix}}")
epicsEnvSet("DESC",            "{{motor.name}} / {{motor.nc_axis.name}}")
epicsEnvSet("EGU",             "{{motor.nc_axis.units}}")
epicsEnvSet("PREC",            "{{motor|pragma('precision', 3) }}")
epicsEnvSet("AXISCONFIG",      "{{motor|pragma('axisconfig', '')}}")
epicsEnvSet("ECAXISFIELDINIT", "{{motor|pragma('additional_fields', '') }}")
epicsEnvSet("AMPLIFIER_FLAGS", "{{motor|pragma('amplifier_flags', '') }}")

EthercatMCCreateAxis("$(MOTOR_PORT)", "$(AXIS_NO)", "$(AMPLIFIER_FLAGS)", "$(AXISCONFIG)")
dbLoadRecords("EthercatMC.template", "PREFIX=$(MOTOR_PREFIX), MOTOR_NAME=$(MOTOR_NAME), R=$(MOTOR_NAME)-, MOTOR_PORT=$(MOTOR_PORT), ASYN_PORT=$(ASYN_PORT), AXIS_NO=$(AXIS_NO), DESC=$(DESC), PREC=$(PREC) $(ECAXISFIELDINIT)")
dbLoadRecords("EthercatMCreadback.template", "PREFIX=$(MOTOR_PREFIX), MOTOR_NAME=$(MOTOR_NAME), R=$(MOTOR_NAME)-, MOTOR_PORT=$(MOTOR_PORT), ASYN_PORT=$(ASYN_PORT), AXIS_NO=$(AXIS_NO), DESC=$(DESC), PREC=$(PREC) ")
dbLoadRecords("EthercatMCdebug.template", "PREFIX=$(MOTOR_PREFIX), MOTOR_NAME=$(MOTOR_NAME), MOTOR_PORT=$(MOTOR_PORT), AXIS_NO=$(AXIS_NO), PREC=3")

{% endfor %}
{% endif %}
{% for db in additional_db_files %}
dbLoadRecords("{{ db.file }}", "{{ db.macros }}")

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
