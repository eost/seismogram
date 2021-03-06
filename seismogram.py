# Import modules
import os
import numpy as np
import h5py
from copy import deepcopy
import scipy.signal as signal

def equalnptsdelta(seism1,seism2):
    'Compare duration and sampling frequency of two seismograms'
    if seism1.delta != seism2.delta or seism1.npts != seism2.npts:
        return False
    return True

def stationsinhdf5(ifile):
    '''
    List stations in hdf5 file
    '''
    f = h5py.File(ifile,'r')
    sta_lst = list(f['STATIONS'])
    f.close()
    return sta_lst

class seismogram(object):
    ''' 
    A simple class that deals with seismograms
    Attributes are:
        depvar: seismogram data
        npts: number of samples
        spec: flag indicating if depvar is given in the time domain (spec=False) 
              or in the frequency domain (spec=True)
    '''
    def __init__(self,ifile=None,stnm=None):
        '''
        Optional Args:
            - ifile: imput data file
            - stnm: name of station to be read
        '''
        if ifile is not None and stnm is not None:
            self.read(ifile,stnm)
        else:
            self.depvar = None
            self.delta  = None
            self.npts   = None
            self.stnm   = None
            self.cmpnm  = None
        self.spec   = False
        self.__name__='Seismogram'
        # All done
        return
        
    
    def readdat(self,ifile,delta):
        '''
        Read dat file
        '''
        assert os.path.exists(ifile), 'Cannot find '+ifile
        self.depvar = np.fromfile(ifile,dtype='int32').astype('float64') # Read and convert to float64
        self.delta = delta
        self.npts  = len(self.depvar)
        # All done
        return

    def read(self,ifile,stnm):
        '''
        Read dat file
        '''
        # Check if file is here
        assert os.path.exists(ifile), 'Cannot find '+ifile
        # Open file and check that the station is available
        f = h5py.File(ifile,'r')
        pathS = '/STATIONS/'+stnm
        assert pathS in f, 'Cannot find station %s in %s'%(stnm,ifile)
        # Read seismic trace
        pathT = pathS+'/Trace'
        self.depvar = np.array(f[pathT])
        self.stnm   = stnm
        self.cmpnm  = f[pathS].attrs['CMPNT']
        self.delta = 1./float(f[pathT].attrs['Fs'])
        self.npts  = len(self.depvar)
        f.close()
        # All done
        return    

    def filter(self, freq, order=4, btype='lowpass'):
        '''
        Bandpass filter the data using a butterworth filter
        Args:
            * freq: A scalar or length-2 sequence giving the critical frequencies (in Hz)
            * order:  Order of the filter.
            * btype: {'lowpass', 'highpass', 'bandpass', 'bandstop'}, optional
              (default is 'lowpass')
        '''
        
        # Check that headers are correct
        assert not self.isempty(), 'Some attributes are missing (e.g., npts, delta, depvar)'

        # Filter design
        if type(freq) is list:
            freq = np.array(freq)
        Wn = freq * 2. * self.delta # Normalizing frequencies
        sos = signal.butter(order, Wn, btype, output='sos')
        
        # Filter waveform
        depvar = signal.sosfilt(sos, self.depvar)
        self.depvar = depvar.astype('float32')

        # All done
        return

    def fft(self):
        '''
        Compute fourier transform and return the seismogram spectrum
        Output: Seismogram spectrum in the frequency domain (type: seismogram)
        '''
        spectrum = self.copy()
        spectrum.spec = True
        spectrum.depvar = np.fft.rfft(self.depvar)        
        
        # All done
        return spectrum

    def ifft(self):
        '''
        Compute the inverse fourrier transform and returns the seismogram spectrum
        Output: Seismogram in the time domain (type: seismogram)
        '''
        seis = self.copy()
        seis.spec = False
        seis.depvar = np.fft.irfft(self.depvar) 
        
        # All done
        return seis
        
    def freq(self):
        '''
        Returns the frequency vector of the current data
        '''
        freq = np.fft.rfftfreq(self.npts,d=self.delta)
        return freq

    def time(self):
        '''
        Returns the time vector of the current data
        '''
        time = np.arange(self.npts)*self.delta
        return time

    def plot(self,ptype=None,xlog=False,ylog=False,**kwargs):
        '''
        Plot the seismogram or spectrum
        Args: All arguments are optional
            - ptype: plot type can be None, 'amp' for absolute amplitude, 'pha' for the phase, 
                     'real' for the real part or 'imag' for the imaginary part.
            - xlog: if True use a log scale on the x axis
            - ylog: if True use a log scale on the y axis
            - *kwargs* can be used to set line properties in pyplot commands (see help of plt.plot)
        examples:
                s.plot(color='r') or s.plot(color='red') will plot the seismogram with a red line
        Use plt.show() to show the corresponding figure
        '''

        # Import the matplotlib module
        import matplotlib.pyplot as plt

        # Check attributes        
        assert not self.isempty(),'Some attributes are missing (e.g., npts, delta, depvar)'

        # Time or frequency vector
        if self.spec is False: # Time vector
            x = self.time()
            xlabel = 'Time, sec'
        else: # Frequency vector
            x = self.freq()
            xlabel = 'Freq., Hz'  
        # What do we want to plot?
        ylabel = 'Amplitude'        
        if ptype is None and not self.spec: # Standard seismogram plot
            y = self.depvar
        elif (ptype is None and self.spec) or ptype == 'amp':  # Amplitude
            y = np.abs(self.depvar)
        elif ptype == 'pha':     # Phase
            y = np.angle(self.depvar)
            ylabel = 'Phase'            
        elif ptype == 'real': # Real part
            y = np.real(self.depvar)
            ylabel = 'Real part amplitude'
        elif ptype == 'imag':
            y = np.imag(self.depvar)
            ylabel = 'Imag. part amplitude'            
        else:
            print('Error: ptype should be None, amp, pha, real or imag')
            return 1        

        # Do we use log scale?
        plotf = plt.plot  # Default: no log scale
        if xlog and ylog: # loglog scale
            plotf=plt.loglog
        elif xlog:        # x log scale
            plotf=plt.semilogx
        elif ylog:        # y log scale
            plotf=plt.semilogy
        
        # Plot seismogram
        lines = plotf(x,y,**kwargs)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        
        # All done
        return lines

    def __add__(self,other):
        '''
        Add two seismograms
        '''
        # Check that everything is all right
        assert not self.isempty(),'Some attributes are missing (e.g., npts, delta, depvar)'
        assert not other.isempty(),'Some attributes are missing (e.g., npts, delta, depvar)'    
        assert equalnptsdelta(self,other), 'Seismograms must have the same duration and sampling freq.'
        
        # Adding files
        res = self.copy()
        res.depvar += other.depvar
    
        # All done 
        return res

    def __sub__(self,other):
        '''
        Substract two seismograms
        '''
        # Check that everything is all right
        assert not self.isempty(),'Some attributes are missing (e.g., npts, delta, depvar)'
        assert not other.isempty(),'Some attributes are missing (e.g., npts, delta, depvar)'
        assert equalnptsdelta(self,other), 'Seismograms must have the same duration and sampling freq.'
        
        # Adding files
        res = self.copy()
        res.depvar -= other.depvar
    
        # All done 
        return res

    def __mul__(self,other):
        '''
        Multiply two seismograms or spectrums
        '''
        # Check that everything is all right
        assert not self.isempty(),'Some attributes are missing (e.g., npts, delta, depvar)'
        assert not other.isempty(),'Some attributes are missing (e.g., npts, delta, depvar)'
        assert equalnptsdelta(self,other), 'Seismograms must have the same duration and sampling freq.'
        
        # Adding files
        res = self.copy()
        res.depvar *= other.depvar
    
        # All done 
        return res    

    def isempty(self):
        '''
        Check if important attributes are there
        '''    
        if (self.npts is None) or (self.delta is None) or (self.depvar is None):
            return True

        # All done
        return False

    def copy(self):
        '''
        Returns a copy of the sac object
        '''
        # All done
        return deepcopy(self)


