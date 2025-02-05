from time import sleep
from math import log10
import logging
from alsamixer import AlsaMixer

class FireFace802(AlsaMixer):

    mixer_sources = {
        'mixer:line-source-gain':  [f'Line {x + 1}' for x in range(8)],
        'mixer:mic-source-gain': [f'MIC {x + 1}' for x in range(4)],
        # 'mixer:spdif-source-gain': [f'SPDIF in {x + 1}' for x in range(2)],
        'mixer:adat-source-gain': [f'ADAT {x + 1}' for x in range(16)]
    }

    mixer_outputs = range(30)


    mixer_outputs_default_names = [f'Line {x + 1}' for x in range(8)] + \
                                       ['Phones 9', 'Phones 10'] + \
                                       ['Phones 11', 'Phones 12'] + \
                                       [f'SPDIF {x + 1}' for x in range(2)] + \
                                       [f'ADAT {x + 1}' for x in range(16)]


    output_meters = {
        'meter:line-output':  range(8),
        'meter:hp-output': range(4),
        # 'meter:spdif-output': range(2),
        'meter:adat-output': range(16)
    }
    meter_noisefloor = -85
    
    


    def __init__(self, *args, **kwargs):

        super().__init__(name='Fireface802', *args, **kwargs)

        """
        Create mixers gain parameters
        """
        for (mixer, sources) in self.mixer_sources.items():

            for output in self.mixer_outputs:

                for source, source_name in enumerate(sources):
                    self.add_parameter(f'{mixer}:{output}:{source}', None, types='i', default=0)
            
                
                self.add_alsa_parameter(f'{mixer}:{output}', None, types='i' * len(sources), alsa_lookup=f'name="{mixer}",index={output}')

                self.add_mapping(
                    src=[f'{mixer}:{output}:{source}' for source, source_name in enumerate(sources)],
                    dest=f'{mixer}:{output}',
                    transform=lambda *v: list(v)
                )


        """
        Output volumes
        """
        for dest in self.mixer_outputs:
            self.add_parameter(f'output:volume:{dest}', None, types='i', default=0)
            self.add_parameter(f'output:volume-db:{dest}', None, types='f', default=0)
            self.add_parameter(f'output:default-name:{dest}', None, types='s', default=self.mixer_outputs_default_names[dest])
            self.add_parameter(f'output:name:{dest}', None, types='s', default='')

            self.add_mapping(
                src=f'output:volume-db:{dest}',
                dest=f'output:volume:{dest}',
                transform=lambda v: v*10,
                inverse=lambda v: v/10,
            )

    
        self.add_alsa_parameter(f'output:volume', None, types='i'*len(self.mixer_outputs))

        self.add_mapping(
            src=[f'output:volume:{dest}' for dest in self.mixer_outputs],
            dest='output:volume',
            transform=lambda *v: list(v)
        )



        """
        Sources gui custom parameters (name, colors, etc)
        """
        sources_types = []
        sources_ids = []

        for (mixer, sources) in self.mixer_sources.items():

            sourcetype = mixer.split(':')[1].split('-')[0]

            for source, source_name in enumerate(sources):

                self.add_parameter(f'source-{sourcetype}-default-name:{source}', None, types='s', default=source_name)
                self.add_parameter(f'source-{sourcetype}-name:{source}', None, types='s', default='')
                self.add_parameter(f'source-{sourcetype}-color:{source}', None, types='s', default='')
                self.add_parameter(f'source-{sourcetype}-hide:{source}', None, types='i', default=0)

                sources_types.append(sourcetype)
                sources_ids.append(source)

        self.add_parameter('sources-types', None, types='s'*len(sources_types), default=sources_types)
        self.add_parameter('sources-ids', None, types='i'*len(sources_ids), default=sources_ids)

        """
        Input options
        """
        for option in ['invert-phase', 'mic-instrument', 'mic-power']:
            for i in range(4):
                self.add_parameter(f'input:{option}:{i}', None, types='i', default=0)

            self.add_alsa_parameter(f'input:{option}', None, types='iiii')
            self.add_mapping(
                src=[f'input:{option}:{i}' for i in range(4)],
                dest=f'input:{option}',
                transform=lambda *v: list(v)
            )

        """
        Meters
        """

        for (mixer, sources) in self.mixer_sources.items():

            sourcetype = mixer.split(':')[1].split('-')[0]

            for source, source_name in enumerate(sources):

                self.add_parameter(f'source-{sourcetype}-meter:{source}', None, types='f', default=-90)


        out_index = -1
        for (output_meter, outputs) in self.output_meters.items():
            for output in outputs:
                out_index += 1
                self.add_parameter(f'output-meter:{out_index}', None, types='f', default=-90)



        self.add_alsa_parameter('metering', None, types='s', default='off')
        self.start_scene('meters', self.update_meters)


    def update_meters(self):
        self.set('metering', 'on')

        while True:
            sleep(1/20)

            if self.get('metering') != 'on':
                
                sleep(0.25)

            else:

                for (mixer, sources) in self.mixer_sources.items():

                    sourcetype = mixer.split(':')[1].split('-')[0]

                    meters = self.alsa_get(f'meter:{sourcetype}-input', f'name="meter:{sourcetype}-input",iface=CARD')
                    if meters:
                        for i, v in enumerate(meters):
                            self.set(f'source-{sourcetype}-meter:{i}', self.meter_abs_to_db(v))

            
                out_index = -1
                for (output_meter, outputs) in self.output_meters.items():

                        meters = self.alsa_get(output_meter, f'name="{output_meter}",iface=CARD')
                        if meters:
                            for i, v in enumerate(meters):
                                out_index += 1

                                self.set(f'output-meter:{out_index}', self.meter_abs_to_db(v))


    def meter_abs_to_db(self, v):
        v = 20*log10(max(v / 134217712,0.00001))
        v = round(v*10) / 10
        if v < self.meter_noisefloor:
            v = -90
        return v

    def create_monitor(self, index, outputs, name=None):
        
        for (mixer, sources) in self.mixer_sources.items():

            sourcetype = mixer.split(':')[1].split('-')[0]

            for source, source_name in enumerate(sources):

                self.add_parameter(f'{mixer.replace('mixer', 'monitor')}:{index}:{source}', None, types='i', default=-65)
                self.add_parameter(f'{mixer.replace('mixer', 'monitor').replace('gain', 'pan')}:{index}:{source}', None, types='f', default=0.5)
                self.add_parameter(f'{mixer.replace('mixer', 'monitor').replace('gain', 'mute')}:{index}:{source}', None, types='i', default=0)
                
                self.add_mapping(
                    src = [
                        f'{mixer.replace('mixer', 'monitor')}:{index}:{source}',
                        f'{mixer.replace('mixer', 'monitor').replace('gain', 'pan')}:{index}:{source}',
                        f'{mixer.replace('mixer', 'monitor').replace('gain', 'mute')}:{index}:{source}',
                        f'source-{sourcetype}-hide:{source}',
                    ],
                    dest = [f'{mixer}:{outputs[0]}:{source}', f'{mixer}:{outputs[1]}:{source}'],
                    transform = lambda volume, pan, mute, hide: self.volume_pan_to_gains(volume, pan, mute or hide, in_range=[-65,6], out_range=[0, 40960])
                )

        default_name = name if name is not None else f'{self.mixer_outputs_default_names[outputs[0]]} + {self.mixer_outputs_default_names[outputs[1]]}'
        self.add_parameter(f'monitor-name:{index}', None, types='s', default=default_name)

        self.add_parameter(f'monitor-master-gain:{index}', None, types='f', default=0)
        self.add_parameter(f'monitor-master-mute:{index}', None, types='i', default=0)

        self.add_mapping(
            src = [f'monitor-master-gain:{index}', f'monitor-master-mute:{index}'],
            dest = [f'output:volume:{outputs[0]}', f'output:volume:{outputs[1]}'],
            transform = lambda volume, mute: self.volume_pan_to_gains(volume, 0.5, mute, in_range=[-65,6], out_range=[-650, 60]),
        )


    def volume_pan_to_gains(self, vol, pan, mute, in_range, out_range):
        # apply mute
        if mute:
            return [out_range[0], out_range[0]]
        # map volume to raw gain -65dB,6dB to 0,40960
        vol = (max(in_range[0], min(in_range[1], vol)) - in_range[0]) / (in_range[1] - in_range[0]) * (out_range[1]-out_range[0]) + out_range[0]
        # apply pan
        pan = max(0, min(1, pan))
        g1 = vol
        g2 = vol
        if pan < 0.5:
            g2 *= pan * 2
        elif pan > 0.5:
            g1 *= 2 - 2 * pan 
        return [g1, g2]