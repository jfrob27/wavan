import numpy as np
from scipy.stats import skew
from imsmooth import imsmooth

###############################################

def apodize(ny, nx, radius):
	"""
	Create edges apodization tapper

	Parameters
	----------
	nx, ny : integers
		size of the tapper
	radius : float
		radius must be lower than 1 and greater than 0.

	Returns
	-------

	tapper : numpy array ready to multiply on your image
				to apodize edges
	"""
	
	if (radius >= 1) or (radius <= 0.):
		print('Error: radius must be lower than 1 and greater than 0.')
		return
	
	ni = np.fix(radius*nx)
	dni = int(nx-ni)
	nj = np.fix(radius*ny)
	dnj = int(ny-nj)
	
	tap1d_x = np.ones(nx)
	tap1d_y = np.ones(ny)
	
	tap1d_x[0:dni] = (np.cos(3. * np.pi/2. + np.pi/2.* (1.* np.arange(dni)/(dni-1)) ))
	tap1d_x[nx-dni:] = (np.cos(0. + np.pi/2. * (1.* np.arange(dni)/(dni-1)) ))
	tap1d_y[0:dnj] = (np.cos(3. * np.pi/2. + np.pi/2. * (1.* np.arange( dnj )/(dnj-1)) ))
	tap1d_y[ny-dnj:] = (np.cos(0. + np.pi/2. * (1.* np.arange(dnj)/(dnj-1)) ))
	
	tapper = np.zeros((ny, nx))
	
	for i in range(nx):
		tapper[:,i] = tap1d_y
		
	for i in range(ny):
		tapper[i,:] = tapper[i,:] * tap1d_x

	return tapper
	
###############################################
	
def padding(input, y, x):

	width = input.shape[1]
	height = input.shape[0]

	output = np.zeros((y,x))
	
	xpos = np.int(x/2 - width/2)
	ypos = np.int(y/2 - height/2)
	
	output[ypos:height+ypos,xpos:width+xpos] = input
	
	return output
	
###############################################

def depad(input, y, x):

	width = input.shape[1]
	height = input.shape[0]
	
	output = np.zeros((y,x))
	
	xpos = np.int(width/2 - x/2)
	ypos = np.int(height/2 - y/2)
	
	output = input[ypos:y+ypos,xpos:x+xpos]
	
	return output
	
###############################################

def uv_plane(na, nb):

	x=np.arange(na)
	y=np.arange(nb)
	x,y=np.meshgrid(x,y)

	if (na % 2) == 0:
		x = (1.*x - (na)/2. )/ na
		shiftx = (na)/2.
		ishiftx = (na)/2.
	else:
		x = (1.*x - (na-1)/2.)/ na
		shiftx = (na-1.)/2.+1
		ishiftx = (na-1.)/2.

	if (nb % 2) == 0:
		y = (1.*y-(nb/2.))/nb
		shifty = (nb)/2.
		ishifty = (nb)/2
	else:
		y = (1.*y - (nb-1)/2.)/ nb
		shifty = (nb-1.)/2+1
		ishifty = (nb-1.)/2.
		
	return x, y, shiftx, shifty, ishiftx, ishifty
	
###############################################

def gauss_segmen(coeff, q=2.5, qdyn=False, skewl=0.4):
	
	module = np.abs(coeff)
	tresh = module.max()
	treshp = module.max()*2.

	while ((treshp-tresh) != 0):
		tresh = treshp
		
		indx = np.where((module <= tresh) & (module > 0.))
		Sigtresh = np.mean((module[indx])**2.)
		treshp = q *np.sqrt(Sigtresh)
					
		#Adjust q according to the skewness
		if ((treshp-tresh) == 0) & (qdyn==True):
			gcoeff = np.where((module <= tresh) & (module > 0.))
			skewn = skew(np.abs(coeff[gcoeff]))
			if skewn > skewl:
				q = q - 0.1
				treshp = module.max()*2.
		
	cohe = np.where(module > tresh)
	gcoeff = np.where((module <= tresh) & (module > 0))
			
	return cohe, gcoeff, q
	
###############################################

def fan_trans(image, reso=1, q=0, qdyn=False, skewl=0.4, pownorm=True, cutpad=True, smooth=False, **kwargs):
	'''
	Performs fan transform on 'image' input (Kirby, J. F. (2005),Computers and
	Geosciences, 31(7), 846-864). If an array of spatial scales is not specified
	returns a quasi-orthogonal basis (Robitaille, J.-F. et al. (2014), MNRAS,
	440(3), 2726-2741).
	
	Parameters
	----------
	image : array_like
		Input array, must be 2-dimentional and real
	scales : array_like, optional
		Array of spatial scales in terms of Fourier wavenumber k
	reso : float, optional
		Resolution of the image in pixel^-1
		
	Returns
	-------
	wt : data cube of wavelet coefficients (complex array)
		wt[scales,nx,ny] -> is the size of the input image
	wav_k : Array of spatial scales used for the decomposition
	S1a : Wavelet power spectrum
		1-dimensional array -> S11(scales)
	'''
	
	#--------------------Definitions----------------------#
	ko= 5.336
	delta = (2.*np.sqrt(-2.*np.log(.75)))/ko
	na = image.shape[1]
	nb = image.shape[0]
	
	nao = np.copy(na)
	nbo = np.copy(nb)
		
	#--------------Apodization--------------------#
	
	if 'apodize' in kwargs:
		tapper = apodize(nb,na,kwargs.get('apodize'))
		image = image *tapper
		
	if 'arrdim' in kwargs:
		arrdim = kwargs.get('arrdim')
		na = arrdim[1]
		nb = arrdim[0]
		image = padding(image,arrdim[0],arrdim[1])
		print na,nb
		
	#--------------Spectral Logarithm--------------------#
	
	if 'scales' in kwargs:
		scales = kwargs.get('scales')
		wav_k = scales
		a2 = 1. / (scales * reso)
		M = scales.size
	
	else:
		nx = np.max(np.array([na,nb]))
		
		M=int(np.log(nx)/delta)
		a2=np.zeros(M)
		a2[0]=np.log(nx)
	
		for i in range(M-1):
			a2[i+1]=a2[i]-delta

		a2=np.exp(a2)
		wav_k = 1. / (a2 * reso)
		
	#-----------------UV-Plane--------------#
	
	x, y, shiftx, shifty, ishiftx, ishifty = uv_plane(na, nb)

	#-----------------Variables--------------#
	
	if cutpad == True:
		sx = nao
		sy = nbo
	else:
		sx = na
		sy = nb
		
	S11 = np.zeros((M,sy,sx))
	wt = np.zeros((M,sy,sx), dtype=complex)

	if (q != 0):
		S1a = np.zeros((3,M))
		S1c = np.zeros((M,sy,sx))
		S1n = np.zeros((M,sy,sx))
		#nS1c = np.zeros((M,sy,sx))
		#nS1n = np.zeros((M,sy,sx))
		W1c = np.zeros((M,sy,sx), dtype=complex)
		W1n = np.zeros((M,sy,sx), dtype=complex)
		S11a = np.zeros((3*M,sy,sx))
		wtcoeff = np.zeros((3*M,sy,sx), dtype=complex)
	else:
		S1a = np.zeros(M)
		S11a = np.zeros((M,sy,sx))
		wtcoeff = np.zeros((M,sy,sx), dtype=complex)
	
	a = ko * a2				#Scales in the wavelet space
	N = int(np.pi/delta)	#Number of orientation for the Morlet wavelet
	
	
	#----------------Wavelet transfom------------------------#
	imFT = np.fft.fft2(image)
	#imFTsh = np.fft.fftshift(image)
	imFT= np.roll(imFT,int(shiftx), axis=1)
	imFT= np.roll(imFT,int(shifty), axis=0)
	
	for j in range(M):
		for i in range(N):
			uv=0.
			t=float(delta*i)
				
			uv=np.exp( -.5*((a[j]*x - ko*np.cos(t))**2. + (a[j]*y - ko*np.sin(t))**2.))
					
			#uv = uv * a[j]		#Energy normalisation on coefficients directly
						
			W1FT = imFT * uv
			W1FT2=np.roll(W1FT,int(ishiftx), axis=1)
			W1FT2=np.roll(W1FT2,int(ishifty), axis=0)
			#Wavelet coefficients 
			W1 = np.fft.ifft2(W1FT2)
			if ('arrdim' in kwargs) & (cutpad == True):
				W1 = depad(W1,nbo,nao)
			
			wt[j,:,:]= wt[j,:,:]+ W1
			S11[j,:,:]= S11[j,:,:] + np.abs(W1)**2.
			
	#----------------Segmentation------------------------#
			if q != 0:
			
				#Set limit based on the noise level of the original
				#power spectrum
				
				cohe, gcoeff, nq = gauss_segmen(W1, q=q[j], qdyn=qdyn, skewl=skewl)
			

				if (W1[gcoeff].shape[0] >  0):
					Wnp = np.zeros((sy,sx), dtype=complex)
					Wnp[gcoeff]=W1[gcoeff]
					W1n[j,:,:] = W1n[j,:,:]+ Wnp
					S1n[j,:,:] = S1n[j,:,:] + np.abs(Wnp)**2.
					Wnp=Wnp*0.
					
				
				if (W1[cohe].shape[0] > 0):
					Wcp = np.zeros((sy,sx), dtype=complex)
					Wcp[cohe]=W1[cohe]
					W1c[j,:,:] = W1c[j,:,:] + Wcp
					S1c[j,:,:] = S1c[j,:,:] + np.abs(Wcp)**2.
					Wcp=Wcp*0.
					
				q[j] = nq
				
		if smooth == True:
			W1ns = W1n[j,:,:]
			W1ns = imsmooth(W1ns, (2.*np.sqrt(2.*np.log(2.)))/(wav_k[j]*reso*2.*np.pi))
			W1n[j,:,:] = W1ns
			del W1ns
			
			W1cs = W1c[j,:,:]
			W1cs = imsmooth(W1cs, (2.*np.sqrt(2.*np.log(2.)))/(wav_k[j]*reso*2.*np.pi))
			W1c[j,:,:] = W1cs
			del W1cs
				
	#----------------Wavelet power spectra---------------#
		
		if pownorm==True:
			if q != 0:
				#Power spectra with scale power normalisation
				S1a[0,j]=np.sum(S11[j,:,:]) * a[j]**2. * delta / (float(N) * na * nb)
				S1a[1,j]=np.sum(S1c[j,:,:]) * a[j]**2. * delta / (float(N) * na * nb)
				S1a[2,j]=np.sum(S1n[j,:,:]) * a[j]**2. * delta / (float(N) * na * nb)
				
				S11a[j,:,:] = S11[j,:,:] * a[j]**2. * delta / float(N)
				S11a[M+j,:,:] = S1c[j,:,:] * a[j]**2. * delta / float(N)
				S11a[2*M+j,:,:] = S1n[j,:,:] * a[j]**2. * delta / float(N)
				
			else:
				S1a[j]=np.sum(S11[j,:,:]) * a[j]**2. * delta / (float(N) * na * nb)
				
				S11a[j,:,:] = S11[j,:,:] * a[j]**2. * delta / float(N)
				
		else:
			if q != 0:
				#Power spectra without scale power normalisation
				S1a[0,j]=np.sum(S11[j,:,:]) * delta / (float(N) * na * nb)
				S1a[1,j]=np.sum(S1c[j,:,:]) * delta / (float(N) * na * nb)
				S1a[2,j]=np.sum(S1n[j,:,:]) * delta / (float(N) * na * nb)
				
				S11a[j,:,:] = S11[j,:,:] * delta / float(N)
				S11a[M+j,:,:] = S1c[j,:,:] * delta / float(N)
				S11a[2*M+j,:,:] = S1n[j,:,:] * delta / float(N)
				
			else:
				S1a[j]=np.sum(S11[j,:,:]) * delta / (float(N) * na * nb)
				
				S11a[j,:,:] = S11[j,:,:] * delta / float(N)
			
	if q != 0:
		wtcoeff[0:M,:,:] = wt
		wtcoeff[M:2*M,:,:] = W1c
		wtcoeff[2*M:3*M,:,:] = W1n
	else:
		wtcoeff = wt
		
	return wtcoeff, S11a, wav_k, S1a, q