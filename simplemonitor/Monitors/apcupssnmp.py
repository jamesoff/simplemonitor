"""
Checks an APC UPS via SNMP using an APC NMC (Network Management card)
"""

from typing import Tuple, cast

import snmp

from .monitor import Monitor, register

# General SNMP OIDs
apcupssnmp_oid_upstype = ".1.3.6.1.4.1.318.1.1.1.1.1.1.0"  # UPS Model Information
# Status
apcupssnmp_oid_battery_capacity = (
    ".1.3.6.1.4.1.318.1.1.1.2.2.1.0"  # current Capacity in %
)
apcupssnmp_oid_battery_runtimeremain = (
    ".1.3.6.1.4.1.318.1.1.1.2.2.3.0"  # runtime remain in timeticks
)
apcupssnmp_oid_output_load = (
    ".1.3.6.1.4.1.318.1.1.1.4.2.3.0"  # Output load in percentage
)
apcupssnmp_oid_upsBasicStateOutputState = (
    ".1.3.6.1.4.1.318.1.1.1.11.1.1.0"  # 64-bit binary String
)
apcupssnmp_oid_upsOutputStatus = ".1.3.6.1.4.1.318.1.1.1.4.1.1.0"  # Output Status
# Health
apcupssnmp_oid_test_result = ".1.3.6.1.4.1.318.1.1.1.7.2.3.0"  # UPS Self Test Result


@register
class MonitorAPCUPSSNMP(Monitor):
    """
    Monitor APC UPS via Direct SNMP queries to management card
    """

    monitor_type = "apcupssnmp"

    def __init__(self, name: str, config_options: dict) -> None:
        super().__init__(name, config_options)
        self.host = cast(str, self.get_config_option("host", required=True))
        self.community = cast(
            str, self.get_config_option("community", required=False, default="public")
        )
        self.maxloadpct = cast(
            int, self.get_config_option("maxloadpct", required=False, default=80)
        )
        self.battpctwarn = cast(
            int, self.get_config_option("battpctwarn", required=False, default=20)
        )
        self.runtimemin = cast(
            int, self.get_config_option("runtimemin", required=False, default=10)
        )
        self.textdelimeter = cast(
            str, self.get_config_option("textdelimeter", required=False, default=",")
        )
        self.snmpengine = snmp.Engine(snmp.SNMPv1)
        self.snmphost = self.snmpengine.Manager(
            self.host, community=self.community.encode("utf-8")
        )

    def DecodeBasicStateOutput(self, error_state, state):
        """decode the 64-bit string encoded state to text"""
        BasicStateOutputTableText = [
            "Abnormal Condition",
            "Running On Battery",
            "LowBattery",
            "OnLine",
            "Replace Battery",
            "Comm:OK",
            "AVR Boost (Low Input V)",
            "AVR Trim (High Input V)",
            "Overload",
            "Runtime Calibration",
            "Batteries Discharged",
            "Manual Bypass",
            "Software Bypass",
            "Bypass - Internal Fault",
            "Bypass - Supply Failure",
            "Bypass - Fan Failure",
            "Sleeping on a Timer",
            "Sleeping until Utility Power Returns",
            "Out:On",
            "Rebooting",
            "Batt Comm Lost",
            "Graceful Shutdown Initiated",
            "Smart Boost/Trim Fault",
            "Bad Output Voltage",
            "Batt Charger Failure",
            "High Batt Temperature",
            "Warning Batt Temperature",
            "Critical Batt Temperature",
            "Self Test In Progress",
            "Low Batt / On Batt",
            "Graceful Shutdown Issued by Upstream Device",
            "Graceful Shutdown Issued by Downstream Device",
            "No Batteries Attached",
            "Synchronized Command is in Progress",
            "Synchronized Sleeping Command is in Progress",
            "Synchronized Rebooting Command is in Progress",
            "Inverter DC Imbalance",
            "Transfer Relay Failure",
            "Shutdown or Unable to Transfer",
            "Low Batt Shutdown",
            "Electronic Unit Fan Failure",
            "Main Relay Failure",
            "Bypass Relay Failure",
            "Temporary Bypass",
            "High Internal Temp",
            "Batt Temp Sensor Fault",
            "Input Out of Range for Bypass",
            "DC Bus Overvoltage",
            "PFC Failure",
            "Critical Hardware Fault",
            "Green/ECO Mode",
            "Hot Standby",
            "EPO Activated",  # Emergency Power Off
            "Load Alarm Violation",
            "Bypass Phase Fault",
            "UPS Internal Comm Failure",
            "Efficiency Booster Mode",
            "Off",
            "Standby",
        ]
        BasicStateOutputTableError = [
            1,
            1,
            1,
            0,
            0,
            0,
            0,
            0,
            1,
            0,
            1,
            1,
            1,
            1,
            1,
            1,
            0,
            0,
            0,
            0,
            0,
            0,
            1,
            1,
            1,
            1,
            1,
            2,
            0,
            1,
            0,
            0,
            1,
            0,
            0,
            0,
            0,
            1,
            0,
            2,
            1,
            2,
            1,
            0,
            1,
            1,
            1,
            1,
            1,
            2,
            0,
            0,
            2,
            0,
            0,
            1,
            0,
            1,
            1,
        ]
        bitlocation = 0
        text = ""
        for bit in state:
            if state[bitlocation] == "1":
                state_text = BasicStateOutputTableText[bitlocation]
                state_status = BasicStateOutputTableError[bitlocation]
                if len(text):
                    text = text + self.textdelimeter + state_text
                else:
                    text = state_text
                # Increase error level as needed - 0 is OK, 1 = Warning, 2 = Error
                error_state = max(error_state, state_status)
            bitlocation += 1
        return error_state, text

    def decodeoutputstatus(self, error_state, val):
        OutputStatusTableText = [
            "unknown",
            "OnLine",
            "OnBattery",
            "OnSmartBoost",
            "TimedSleeping",
            "SoftwareBypass",
            "OFF",
            "Rebooting",
            "SwitchedBypass",
            "HardwareFailureBypass",
            "SleepingUntilPowerReturn",
            "OnSmartTrim",
            "EcoMode",
            "HotStandby",
            "OnBatteryTest",
            "EmergencyStaticBypass",
            "StaticBypassStandby",
            "PowerSavingMode",
            "SpotMode",
            "eConversion",
        ]
        OutputStatusTableError = [
            1,
            0,
            1,
            0,
            1,
            1,
            2,
            1,
            1,
            2,
            1,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        ]
        return OutputStatusTableError[val - 1] + error_state, OutputStatusTableText[
            val - 1
        ]

    def decodeselftest(self, error_state, val):
        """Decode the Last Calibration value to text"""
        tabletext = ["Pass", "Never", "InProg", "Never"]
        tableerror = [0, 1, 0, 1]
        return tableerror[val - 1] + error_state, tabletext[val - 1]

    def snmpresulttext(self, result):
        for name, val in result:
            # print(f"X:{dir(val)}:X")
            if isinstance(val, snmp.smi.Gauge32):
                print(f"State: {name}  @ {int(val.value)}")
            elif isinstance(val, snmp.smi.OctetString):
                print(f"State: {name}  # {val.data.decode('utf-8')}")
            elif isinstance(val, snmp.smi.Integer32):
                print(f"State: {name}  @ {int(val.value)}")
            elif isinstance(val, snmp.smi.TimeTicks):
                print(f"State: {name}  % {int(val.value / 6000)}m")
            else:
                print(f"State: {name}  $ {str(val)}")

    def processbattpct(self, error_state, batt_pct):
        if batt_pct < self.battpctwarn:
            error_state += 1
        return error_state, batt_pct

    def processloadpct(self, error_state, load_pct):
        if load_pct > self.maxloadpct:
            error_state += 1
        return error_state, load_pct

    def processruntime(self, error_state, runtimeval):
        runtime = int(runtimeval / 6000)  # Convert to minutes
        if runtime < self.runtimemin:
            error_state += 1
        return error_state, str(runtime) + "m"

    def geterrorstatetext(self, error_state):
        if error_state > 1:
            error_text = f"CRIT{error_state}"
        elif error_state == 1:
            error_text = "WARN"
        else:
            error_text = "OK"
        return error_text + " - "

    def run_test(self) -> bool:
        state = self.snmphost.get(
            apcupssnmp_oid_upstype,
            apcupssnmp_oid_upsBasicStateOutputState,
            apcupssnmp_oid_battery_capacity,
            apcupssnmp_oid_output_load,
            apcupssnmp_oid_upsOutputStatus,
            apcupssnmp_oid_test_result,
            apcupssnmp_oid_battery_runtimeremain,
        )
        error_state = 0
        ups_type = state[0].value.data.decode("utf-8")
        error_state, status_state = self.DecodeBasicStateOutput(
            error_state, state[1].value.data.decode("utf-8")
        )
        error_state, batt_pct = self.processbattpct(error_state, state[2].value.value)
        error_state, load_pct = self.processloadpct(error_state, state[3].value.value)
        error_state, outputstate = self.decodeoutputstatus(
            error_state, state[4].value.value
        )
        error_state, selftest = self.decodeselftest(error_state, state[5].value.value)
        error_state, runtime = self.processruntime(error_state, state[6].value.value)
        error_text = self.geterrorstatetext(error_state)
        output_text = error_text + self.textdelimeter.join(
            [
                f"{ups_type}:{status_state}",
                f"Batt:{batt_pct}%",
                f"Load:{load_pct}%",
                f"Runtime:{runtime}",
                f"OutStatus:{outputstate}",
                f"Test:{selftest}",
            ]
        )
        # print(output_text)
        if error_state:
            return self.record_fail(output_text)
        return self.record_success(output_text)

    def get_params(self) -> Tuple:
        return (
            self.host,
            self.community,
            self.maxloadpct,
            self.battpctwarn,
            self.runtimemin,
            self.textdelimeter,
            self.snmpengine,
        )

    def describe(self) -> str:
        return "Checking Status & Health of APC UPS {} via SNMP".format(self.host)
