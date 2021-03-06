from datetime import datetime,timedelta
import numpy as np
from xarray import DataArray
import scipy.signal as signal
from matplotlib.pyplot import figure, gca,subplots
#
from .fwdmodel import plasmaprop
#
DTPG = 0.1

def spec(sig, Fs:int, flim=None, t0:datetime=None, ftick=None, vlim=(None,None), zpad=1, ttxt=''):
    """
    sig: signal to analyze, Numpy ndarray
    """
    if sig is None:
        return

    twin = 0.001 # time length of windows [sec.]
    Nfft = max(64, int(zpad*Fs*twin))
  #  Nol = int(Fs*twin/2)  # 50% overlap


    fg = figure()
    if 1: #sig.size > 5*Nfft:  # arbitrary criteria
        ax = fg.add_subplot(2,1,1)
        f,t,Sxx = signal.spectrogram(sig,
                                     fs=Fs,
                                     nfft= Nfft,
                                     nperseg= Nfft,
                                     noverlap= None,
                                     return_onesided=False) # [V**2/Hz]

        if isinstance(t0,datetime):
            t = [t0 + timedelta(seconds=T) for T in t]
        elif t0 is not None:
            t = [t0[0] + T for T in t]


        f = np.fft.fftshift(f)
        Snorm = np.fft.fftshift(Sxx/Sxx.max(),axes=0) + 1e-10
# %%
        if Fs>=1e6:
            ttxt += f'$f_s$={Fs/1e6} MHz  Nfft {Nfft}  '
        else:
            ttxt += f'$f_s$={Fs/1e3} kHz  Nfft {Nfft}  '
        if isinstance(t0,datetime):
            ttxt += datetime.strftime(t0,'%Y-%m-%d')
        fg.suptitle(ttxt, y=0.99)

        h=ax.pcolormesh(t, f, 10*np.log10(Snorm), vmin=vlim[0])
        fg.colorbar(h,ax=ax).set_label('PSD (dB)')
        ax.set_ylabel('frequency [Hz]')
        ax.set_xlabel('time')
        ax.set_title('Spectrogram')
        ax.autoscale(True,'both',tight=True)
        if flim:
            ax.set_ylim(flim)
        if ftick is not None:
            for ft in ftick:
                ax.axhline(ft,color='red',linestyle='--')
    else:
        t=ts = Sxx = ax = None
#%%
    Np = 2 if ax is not None else 1
    ax = fg.add_subplot(Np,1,Np)

    #dtw = 2*DTPG #  seconds to window
    #tstep = np.ceil(DTPG*Fs)
    #wind = np.ceil(dtw*Fs);
    #Nfft = zeropadfactor*wind

    if 1:
        f,Sp = signal.welch(sig,Fs,
                        nperseg=Nfft,
                        window = 'hann',
    #                    noverlap=Nol,
                        nfft=Nfft,
                        return_onesided=False
                        )

    if 0: # simpler single FFT-based method
        from tincanradar import psd
        Sp, f = psd(sig, Fs, zpad, np.hanning)

    ttxt = 'time-averaged spectrum,  Nfft {}, Fs {} Hz'.format(Nfft, Fs)

    if isinstance(t0, datetime):
        ts = (datetime.strftime(t[0],'%H:%M:%S'), datetime.strftime(t[-1],'%H:%M:%S'))
    elif t is not None:
        ts = (t[0], t[-1])
    elif t0 is not None:
        ts = (t0[0], t0[1])
    else:
        ts = None

    if ts is not None:
        ttxt += ', t={:.1f}..{:.1f}'.format(ts[0], ts[-1])

    ax.plot(f, 10*np.log10(Sp))
    ax.set_ylabel('PSD [dB/Hz]')
    ax.set_xlabel('frequency [Hz]')
    ax.set_ylim(vlim)
    ax.set_title(ttxt)
    ax.autoscale(True,'x',True)
    ax.grid(True)

    if flim:
        ax.set_xlim(flim)
# %% analysis
    if ftick is not None:
        for ft in ftick:
            ax.axvline(ft,color='red',linestyle='--')

    fg.tight_layout()

    return f,t,Sxx,Sp


def constellation_diagram(sig):
    ax = figure().gca()
    ax.scatter(sig.real, sig.imag)
    ax.axhline(0, linestyle='--', color='gray', alpha=0.5)
    ax.axvline(0, linestyle='--', color='gray', alpha=0.5)
    ax.set_title('Constellation Diagram')


def plotraw(tx:np.ndarray, rx:np.ndarray, fs:int, Nraw:int=10000):
    ax = None

    if tx is not None:
        t = np.arange(0, tx.size/fs, 1/fs)[:tx.size] # sometimes off-by-one

        ax = figure().gca()
        ax.plot(t[:Nraw], tx[:Nraw].real, 'b', label='TX')

    if rx is not None:
        t = np.arange(0, rx.size/fs, 1/fs)

        if ax is None:
            ax = figure().gca()

        ax.plot(t[:Nraw], rx[:Nraw].real, 'r--', label='RX')
        ax.legend()

    if ax is None:
        return

    ax.set_title(f'raw waveform, first {t[:Nraw].size} points')
    ax.set_xlabel('time [sec]')
    ax.set_ylabel('amplitude')


def plotxcor(Rxy, fs:int, ax=None):
    if Rxy is None:
        return

    lags = np.arange(Rxy.size) - Rxy.size // 2
# %%
    if ax is None:
        ax = gca()

    ax.cla()

    ax.plot(lags, Rxy.real)
    ax.set_xlabel('lags')
    ax.set_ylabel('Rxy')


    ax.set_title(f'Cross-correlation @ $f_s$={fs/1e6:.1f} Ms/s')

    return ax

# %% forward model
def summary(iono:DataArray, reflectionheight, f0,latlon, dtime):
    assert isinstance(iono,DataArray)

    ax = figure().gca()
    ax.plot(iono.loc[:,'ne'],iono.alt_km,'b',label='$N_e$')

    if reflectionheight is not None:
        ax.axhline(reflectionheight,color='m',linestyle='--',label='reflection height')

    ax.legend()
    ax.set_ylabel('altitude [km]')
    ax.set_xlabel('Number Density')

    ax.autoscale(True,'y',tight=True)
    ax.set_title(f'({latlon[0]}, {latlon[1]})  {dtime}  @ {f0/1e6:.1f} MHz',y=1.06)

def sweep(iono,fs,B0,latlon,dtime):
    hr = np.zeros(fs.size)
    for i,f in enumerate(fs):
        wp,wH,hr[i] = plasmaprop(iono,f,B0)

    ax = figure().gca()
    ax.plot(fs/1e6, hr)
    ax.set_xlabel('frequency [MHz]')
    ax.set_ylabel('altitude [km]')
    ax.set_title('Reflection Height: first order approx. $\omega_p = \omega$')

def plotR(R,zkm):
    ax = figure().gca()
    if R is not None:
        ax2 = ax.twiny()
        #ax2.plot(dNe,zkm,'r',label='$ \partial N_e/\partial z $')

        ax2.plot(R,zkm,'r',label='$\Gamma$')

        ax2.legend(loc='right')

def plotgas(iono,dens,temp,vm,time,latlon,ap,f107):
    """
    iono: from IRI
    dens,temp: from MSIS
    """

    fg,axs = subplots(1,3,sharey=True)
    ax = axs[0]
    ax.semilogx(iono.loc[:,'ne'],iono.alt_km,label='$N_e$')
    ax.semilogx(dens.loc[:,'O2'],dens.alt_km,label='$N_{O_2}$')
    ax.semilogx(dens.loc[:,'N2'],dens.alt_km,label='$N_{N_2}$')
    ax.legend()
    ax.set_ylabel('altitude [km]')
    ax.set_xlabel('density [m^-3]')

    ax = axs[1]
    ax.plot(iono.loc[:,'Te'],iono.alt_km, label='$T_e$')
    ax.plot(temp.loc[:,'Tn'], temp.alt_km, label='$T_n$')
    ax.set_xlabel('temperature [K]')
    ax.legend()
    ax.autoscale(True,'y',True)

    ax = axs[2]
    ax.semilogx(vm,vm.alt_km)
    ax.set_xlabel('Collision frequency [Hz]')
    ax.set_title('Electron-neutral collision frequency\n'
                 'D and E region ionosphere')

    fg.suptitle(f'{time} {latlon}  ap={ap} f107={f107}')

def plotloss(Li,Fr,t):
    ax = figure().gca()
    ax.plot(Fr/1e6,Li)
    ax.set_xlabel('Frequency [MHz]')
    ax.set_ylabel('loss [dB]')
    ax.set_title(f'{t} D and E region full path loss')
