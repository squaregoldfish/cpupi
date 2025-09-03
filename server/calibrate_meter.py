from rpi_hardware_pwm import HardwarePWM

def set_meter_percent(meter, percent):
    try:
        meter_value = float(percent)
        if meter_value < 0:
            meter_value = 0
        elif meter_value > 100:
            meter_value = 100

        meter.change_duty_cycle(meter_value)
    except:
        pass


cpu_meter = HardwarePWM(pwm_channel=0, hz=60, chip=0)
cpu_meter.start(0)
mem_meter = HardwarePWM(pwm_channel=1, hz=60, chip=0)
mem_meter.start(0)

while True:
    percent = input('Set percentage: ')
    set_meter_percent(cpu_meter, percent)
    set_meter_percent(mem_meter, percent)