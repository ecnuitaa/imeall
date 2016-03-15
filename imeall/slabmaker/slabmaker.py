from ase.io import read
from ase.visualize import view
from ase.io import write
from ase.lattice.spacegroup import crystal
from ase.lattice.surface import surface,bcc111,bcc110
from ase.lattice.cubic import BodyCenteredCubic

from collections import Counter

import numpy as np
import transformations as quat

def make_interface(slab_a, slab_b, dist):
	interface = slab_a.copy()
#we will fuse along z direction so fe the highest z-component 
#of bottom slab. Then align top slab according to this.
	zmax = interface.get_positions()[:,2].max()
	slab_b.center(vacuum = zmax + dist , axis=2)
	interface.extend(slab_b)
	interface.center(vacuum=0.0)
	return interface

def compare_latt_vecs(cell_a, cell_b):
# works for orthorhombic cells:
  ratios = [a[0]/a[1] for a in zip(np.diag(cell_a), np.diag(cell_a))]
  return ratios

def rotate_plane_z(grain, miller):
	# rotates atoms in grain so that planes parallel to plane
	# defined by miller index n is in the xy plane.
	z = np.array([0.,0., -1.])
	p = np.cross(z, miller)
  # angle between line on plane and z-axis
	theta = np.arccos(miller.dot(z)/(np.linalg.norm(miller)*(np.linalg.norm(z))))
	print '\t Aligning Orientation axis with rotation: ', theta
	print '\t around : ', p, '\n'
	rotation_quaternion = quat.quaternion_about_axis(theta, p)
	grain = rotate_grain(grain, theta, p)
	return rotation_quaternion

def rotate_plane_xy(grain, miller):
# rotates atoms in grain so that a line in the plane 
# defined by miller index n is parallel to x.
# This is equivalent to making the miller index parallel to y.
	z = np.array([1., 0., 0.])
	p = np.cross(z, miller)
#	angle between line on plane and desired line:
	theta = np.arccos(miller.dot(z)/(np.linalg.norm(miller)*(np.linalg.norm(z))))
	print '\t Rotated miller index: ', miller.round(3)
	print '\t Aligning miller plane with y axis by angle: ', theta*(180./np.pi)
	print '\t around : ', p.round(3), '\n'
#	print 'theta', theta
	rotation_quaternion = quat.quaternion_about_axis(theta, p)
	print '\t vec: ', rotate_vec(rotation_quaternion, miller).round(3)
	grain = rotate_grain(grain, q = rotation_quaternion)
	return rotation_quaternion

def generate_mirror(grain, point, miller):
#reflection matrix for plane around point
#with miller index as normal to that plane
	M = quat.reflection_matrix(point, miller)	
	print 'mirror plane', M
	for atom in grain:
		p = atom.position
		p_prime = M[:3,:3].dot(p)
		atom.position = p_prime
#
#  From  zeiner we have the following theorem and wisdom:
#  Firstly a lattice is coincident if and only if it 
#  is an orthogonal matrix with rational entries.
#  The general relationship between a rotation axis, rotation, and a 
#  quaternion can be written:
#  In order to be pure we should !!not!! do the rotations in terms of !!Degrees!!
#  It is superior to do the rotation in terms of an integral number of radians.
#  Then we can exploit all of Zeiner's relationships. For instance:
#  quaternion               rotation angle \psi and the lattice 
#  direction of the rotation axis.
#  Additionally the coincidence index can be given by
#  m is angle of rotation in radians, atoms is the grain to be rotated
# (m,n,0,0) := \psi = \arccos(\frac{m^{2} - n^{2}}{m^{2} + n^{2}}), [100]
#

def find_sigma_csl(q):
# \Sigma(R(\mathbf{r})) = |\mathbf{r}|^{2}/2^{l} where l is the maximal power such that
# 2^{l} divides |\mathbf{r}|^{2}.
	r   = q.dot(q)
	div = r
	l   = 0
	while div >= 1:
		div = r/np.power(2,l)
		l += 1
	return sigma
# m is angle of rotation in radians
#(m,n,n,0) := \psi = \arccos(\frac{m^{2} - 3n^{2}}{m^{2} + 3n^{2}}), [111]
#(k,lambda,mu,nu)   :=
#				\psi = \arccos(\frac{k^{2} - \lambda^{2} - \mu^{2} -\nu^{2}}{k^{2} +
#					  +  \lambda^{2} + \mu^{2} + \nu^{2}}), [\lambda\mu\nu]
def gnu_plot_gb(boundary_plane, m, invm, mb=0.0, invmb=0.0, gb_id='0000000000'):
# output gnuplot script to generate "CSL plots on the fly"
# should be equation of line for given miller plane
	f = open('plot.gnu', 'w')
	script = " \
#	g(x) = {2}*x \n \
	h(x) = {3}*x \n \
#	gb(x) = {4}*x \n \
#	hb(x) = {5}*x \n \
	set xr[-10:10] \n \
	set yr[-15:15] \n \
	pl   'grainaT.dat' u 1:2 w p pt 7 ps 1.5 lt 1 t 'Grain A' \n \
	repl 'grainaB.dat' u 1:2 w p pt 6 lt 1.0      t ''        \n \
	repl 'grainbT.dat' u 1:2 w p pt 7 ps 1 lt 3 t 'Grain B' \n \
	repl 'grainbB.dat' u 1:2 w p pt 6 ps 1 lt 3 t ''        \n \
#	repl g(x) lt -1 t '({0})' \n \
	repl h(x) lt -1 t '({0})' \n \
#	repl gb(x) lt 3 t '' \n \
#	repl hb(x) lt 3 t '' \n \
	set terminal pngcairo     \n \
	set output 'csl_{1}.png'  \n \
	repl \n \
	set terminal x11 \n".format(boundary_plane, gb_id, m, invm, mb, invmb)
	print >> f, script
	f.close()

def bcc_csl_nn0(m, n, grain):
# m
#(m,n,n,0) := \psi = \arccos(\frac{m^{2} - 2n^{2}}{m^{2} + 2n^{2}}), [110]
# once m and n have been chosen according to some scheme we generate the rotation
# matrix
	#R = quat.quaternion_matrix([m,n,n,0])
	R = zeiner_matrix(np.array([m,n,n,0]))
#project down to 3x3:
	Rp = np.identity(4)
	Rp[:3,:3] = R
	qp = quat.quaternion_from_matrix(Rp, isprecise=True)
	print 'quaternion from matrix', qp.round(2)
	for i in range(len(grain)):
		grain[i].position = np.dot(R, grain[i].position)

def zeiner_matrix(q):
	r2 = q.dot(q)
	k = q[0]
	l = q[1]
	m = q[2]
	n = q[3]
	R = np.array([
        [ k*k+l*l-m*m-n*n,   -2*k*n + 2*l*m,    2*k*m + 2*l*n],
        [   2*k*n + 2*l*m,  k*k-l*l+m*m-n*n, -2*k*l + 2*m*n],
        [  -2*k*m + 2*l*n, 2*k*l + 2*m*n,  k*k-l*l-m*m + n*n]
				])
# The zeiner matrix refers to the rotation matrix
# for the lattice:
#	R = (1./r2)*R.T
	R = (1./r2)*R
	return R

def csl_lattice_vecs(m,n):
#
# rational orthogonal matrices can be parameterized
# by integral quaternions, i.e. by quaternions with integral coefficients or
# a quaternion with integral coefficients + 1/2(1 1 1 1).
# an integral quaternion is primitive if the greatest divisor of its integral components is 1.
# for a primitive quaternion \mathbf{r} = (r_0,r_1,r_2,r_3)
# r^{0} = [ r_{1}, r_{2}, r_{3}]
# r^{1} = [r_{0}, r_{3}, -r_{2}]
# r^{2} = [-r_{3}, r_{0}, r_{1}]
# r^{3} = [r_{2}, -r_{1}, r_{0}]
# Given a bcc lattice (Zeiner05) we can define the
# lattice vectors of the coincident site lattice as
# r^{0}, r^{1}, r^{2}, r^{3}, 1/2(r^{0} + r^{1} + r^{2} + r^{3}),  if |r|^{2} is odd
# r^{0}, 1/2(r^{0}+r^{1}), 1/2(r^{0} + r^{2}), 1/2(r^{0} + r^{3}), if 2 divides |r|^2
# and 4 does not divide |r|^{2}
# 1/2 r^{0}, 1/2 r^{1}, 1/2r^{2}, 1/2 r^{3} if 4 divides |r|^2
# There is then a straight forward procedure to obtain a 2d lattice
# for the grain boundary. Just take the miller plane defining the boundary
# and pick a set of independent vectors from the lattice vectors of the CSL.
#
	r = np.array([m,n,n,0])
	r0 = np.array([r[1], r[2],  r[3]])
	r1 = np.array([r[0], r[3], -r[2]])
	r2 = np.array([-r[3], r[0], r[1]])
	r3 = np.array([r[2], -r[1], r[0]])

	if np.mod(r.dot(r),2)==1:
		print '\t |r|^{2} is odd'
		a = r0
		b = r1
		c = r2
		d = 0.5*(r0 + r1+ r2 +r3)
	elif (np.mod(r.dot(r), 2) == 0 and np.mod(r.dot(r),4) != 0):
		print '\t |r|^{2}  is divisible by 2 but not 4'
		a = r0
		b = 0.5*(r0 +r1)
		c = 0.5*(r0+r2)
		d = 0.5*(r0 + r3)
#	elif mod(r.dot(r), 4)==0:
	else:
		print '\t |r|^{2}  is divisible 4'
		a = 0.5*r0
		b = 0.5*(r1)
		c = 0.5*(r2)
		d = 0.5*(r3)
	return np.array([a,b,c,d])

def rotate_vec(q, vec):
#rotate 3 vector with quaternion
	vec = np.array([0, vec[0], vec[1], vec[2]])
	qm = quat.quaternion_conjugate(q)
	pos_prime = quat.quaternion_multiply(q, vec)
	pos_prime = quat.quaternion_multiply(pos_prime, qm)
	vec = quat.quaternion_imag(pos_prime)
	return vec

def rotate_grain(grain, theta=0., x=[0.,0.,0.], q=[]):
# rotate the grain according to quaternion = [Theta, u,v,w] = [w,x,y,z]
# need theta/2 but this is handled correctly in quaternion_about_axis
# from the transformation library:
# Standard routine is passed angle and vector
# this generates the quaternion to do the rotation 
# however if a quaternion, q!=None, is passed to routine the plane is rotated
# using q.
	if q==[]:
		q = quat.quaternion_about_axis(theta, x)
		qm = quat.quaternion_conjugate(q)
	else:
		qm = quat.quaternion_conjugate(q)

	for i in range(len(grain)):
		pos = np.array([0, grain[i].position[0], grain[i].position[1], grain[i].position[2]])
		pos_prime = quat.quaternion_multiply(q, pos)
		pos_prime = quat.quaternion_multiply(pos_prime, qm)
		grain[i].position = quat.quaternion_imag(pos_prime)
	return grain

def print_points(atoms, f):
	for atom in atoms:
		print>>f, '{0:12.7f} {1:12.7f} {2:12.7f}'.format(atom.position[0], atom.position[1], atom.position[2])

def find_densest_plane(grain_dict):
	maxx = max([len(a) for a in grain_dict.values()])
	len_keys = {x:len(y) for x,y in grain_dict.items()}
	keys_2   = [x for x,y in grain_dict.items()]
	keys_2   = sorted(keys_2)
	keys = [x for x,y in grain_dict.items() if len(y) == maxx]
	print '\t Largest number of points: ', maxx, 'Number of z-planes: ', len(keys)
	key1 = keys[0]
	z_below = keys_2.index(key1)-1
	key2 = keys_2[z_below]
	return key1, key2

def simplify_csl(m, b=0.00):
# Simplify the dat files of the csl so that atoms in grain_a are below the line
# defined by the boundary plane in the current projection and atoms from grain_b
# are above.
	graina_list = ['grainaT.dat', 'grainaB.dat']
	grainb_list = ['grainbT.dat', 'grainbB.dat']
	for name in graina_list:
		f = open('{0}'.format(name),'r+')
		grain_a = f.read().split('\n')
		f.close()
		f = open('{0}'.format(name),'w')
		del(grain_a[-1])
		for at in grain_a:
			position = np.array(map(float, at.split()))
			if ( round(position[1]- m*position[0]-b,2) <= 0.0):
			#if ( round(position[0],2) <= 0.0):
				print>>f, '{0:12.7f} {1:12.7f} {2:12.7f}'.format(position[0], position[1], position[2])
			else:
				pass
		f.close()
	for name in grainb_list:
		f = open('{0}'.format(name),'r+')
		grain_b = f.read().split('\n')
		f.close()
		f = open('{0}'.format(name),'w')
		del(grain_b[-1])
		for at in grain_b:
			position = np.array(map(float, at.split()))
			if (round(position[1]-m*position[0]-b,2) >= 0.0):
			#if (round(position[0],2) >= 0.0):
				print>>f, '{0:12.7f} {1:12.7f} {2:12.7f}'.format(position[0], position[1], position[2])
			else:
				pass
		f.close()

def csl_factory(orientation_axis, miller, boundary_plane, m, n, grain_a, grain_b, mode='Zeiner'):
	f = open('grainaT.dat','w')
	g = open('grainaB.dat','w')
# rotate_plane takes grain a and rotates it
# so that the orientation axis of the grain boundary with
# respect to grain a is orthogonal to the x-y plane this is for,
# and the miller index of the boundary_plane is !perpendicular to the x-axis.
# ease of visualization.
	plane_quaternion_z = rotate_plane_z(grain_a, miller)
	print '\t boundary plane', boundary_plane.round(2)
	plane_quaternion_x = rotate_plane_xy(grain_a, rotate_vec(plane_quaternion_z, boundary_plane))
# The following code finds the planes with largest number
# of points for viewing purposes:
# First we sort grain_a by x, y, z
	grain_a = sorted(grain_a, key=lambda x: (x.position[2], x.position[0], x.position[1]))
	z_vals = []
# The loop over each position in grain_a and store the z-value
# in a list.
	for grain in grain_a:
		if round(grain.position[2], 2) not in [round(z,2) for z in z_vals[:]]:
			z_vals.append(round(grain.position[2],2))
	grain_dict = {}
# initialize dictionary of lists
	for z in z_vals:
		grain_dict[z] = []
# append the atoms to each position in the dictionary.
	for grain in grain_a:
		grain_dict[round(grain.position[2], 2)].append(grain)
# create a list of z-values and the number of points for each z value
	len_list = []
	for z in z_vals:
		 len_list.append((z, len(grain_dict[z])))
# this is a handy construction:
#	keys = [x for x,y in grain_dict.items() if len(y) == maxx]
	key1, key2 = find_densest_plane(grain_dict)
	print_points(grain_dict[key1], f)
	print_points(grain_dict[key2], g)
	f.close()
	g.close()
# Setup grain b and project into chosen plane
	f = open('grainbT.dat','w')
	g = open('grainbB.dat','w')
# Rotates grain according to angle and orientation axis
	if mode=='Zeiner':
# theta = np.pi*(60.00/180.)
# bcc_csl_nn0(6,1,grain_b)
# We need to generate the rotation matrix R(\theta) from the quaternion.
		print '\t Using Zeiner'
		print '\t Spanning Vectors of CSL'
		print '\t', csl_lattice_vecs(m,n)
		print ''
		bcc_csl_nn0(m, n, grain_b)
# A rotation is a coincidence rotation if the rotation
# matrix is orthogonal and has rational entries.
		rotm = zeiner_matrix(np.array([m,n,n,0]))
		print rotm
		mn = float(m*m-2*n*n)/float(m*m+2*n*n)
		angle_of_rotation = np.arccos(mn)
		deg = round(angle_of_rotation*(180./np.pi),2) 
		print m , n
		print 'Angle of rotation: ', deg, 'or ', 180.-deg, ' Orientation Axis: ', (n, n, 0)
	else:
		theta = np.arccos(float(m-2*n*n)/float(m+2*n*n))
		rotate_grain(grain_b, theta, orientation_axis)

	intercept = np.array([0.0, 0.0, 1.0])
	boundary_plane = rotate_vec(plane_quaternion_z, boundary_plane)
	boundary_plane = rotate_vec(plane_quaternion_x, boundary_plane)

	intercept = rotate_vec(plane_quaternion_z, intercept)
	intercept = rotate_vec(plane_quaternion_x, intercept)

	print ''
	print 'Choose a boundary plane. For pure tilt grain boundary this should be orthogonal'
	print 'to the orientation axis. '
	print ''
	print 'Boundary plane: ', boundary_plane.round(3)
	print 'Intercept: ', intercept.round(3)
	print 'Slope of line in x,y plane'
# Draw a line on the graph which is the 
# equation of the line defining the miller index
# and a line perpendicular to this which corresponds
# to a line in the plane.
#	m = (boundary_plane[0]/boundary_plane[1])
#	invm = -(1./(boundary_plane[0]/boundary_plane[1]))
# Grain boundary should be parallel to \hat{x}
	m    = 0.
	invm = 0.
	print '   m = ', m
	print 'invm = ', invm
#
# The boundary_plane vector is the miller index
# of the grain boundary with respect to initial crystal
# for grain b we rotate this around orientation axis
# by the orientation angle and then.
#
	boundary_plane_b = boundary_plane
	print boundary_plane_b
	boundary_plane_b = np.dot(rotm, boundary_plane_b)
	print '\t Rotated Grain Boundary:' 
#	print  boundary_plane_b
	boundary_plane_b = rotate_vec(plane_quaternion_z, boundary_plane_b)
	boundary_plane_b = rotate_vec(plane_quaternion_x, boundary_plane_b)
#	print rotm
	print '\t', boundary_plane_b
	mb    = 0.
	invmb = 0.
#	print 'm    = ', mb
#	print 'invm = ', invmb
	gnu_plot_gb('Plane', m, invm, mb=mb, invmb=invmb)
# No we rotate grain_b into xy plane for visualization purposes.
	rotate_grain(grain_b, q=plane_quaternion_z)
	rotate_grain(grain_b, q=plane_quaternion_x)
	grain_b = sorted(grain_b, key=lambda x: (x.position[2], x.position[0], x.position[1]))
	z_vals = []
	for grain in grain_b:
		if round(grain.position[2], 2) not in [round(z,2) for z in z_vals[:]]:
			z_vals.append(round(grain.position[2],2))
	grain_dict = {}
	for z in z_vals:
		grain_dict[z] = []
	for grain in grain_b:
		grain_dict[round(grain.position[2], 2)].append(grain)
	len_list = []
	for z in z_vals:
		 len_list.append((z,len(grain_dict[z])))
#	maxx = max([len(a) for a in grain_dict.values()])	
#	keys = [x for x,y in grain_dict.items() if len(y) == maxx ]
	key1, key2 = find_densest_plane(grain_dict)
	print_points(grain_dict[key1], f)
	print_points(grain_dict[key2], g)
	f.close()
	g.close()
	simplify_csl(0.)

#BCC Iron unit cell
if __name__=='__main__':
	a  = 2.834
	fe = crystal('Fe', [(0,0,0)], spacegroup=229,
	             cellpar=[a, a, a, 90, 90, 90],size=[10,10,10])
	grain_a = fe.copy()
	grain_b = fe.copy()
	for i in range(3):
		grain_a.positions[:,i] -= 10*a/2.
		grain_b.positions[:,i] -= 10*a/2.
	orientation_axis = np.array([1, 1, 0])
	miller           = np.array([1, 1, 0])
	theta = np.pi*(70.53/180.)
	boundary_plane   = np.array([1, -1, 1])
	refl = quat.reflection_matrix(np.array([0.,-1,0]), boundary_plane)
	print refl
	refl_quat = quat.quaternion_from_matrix(refl)
	print refl_quat
#	theta            = np.pi*(50.48/180.)
#	boundary_plane   = np.array([3, -3, 2])
#	theta = np.pi*(38.94/180.)
# boundary_plane   = np.array([-1, 1, 4])
#	boundary_plane   = np.array([-1, 1, 3])
#	theta            = np.pi*(129.52/180.)
#	boundary_plane   = np.array([-2, 2, 1])
#	boundary_plane   = np.array([3, -3, 4])
#	theta = np.pi*(109.47/180.)
#	theta = np.pi*(141.06/180.)
#	theta = np.pi*(86.63/180.)
	m2 = 2*(1.+np.cos(theta))/(1.-np.cos(theta))
	print ''
	print '\t m squared: ', np.sqrt(m2), np.sqrt(m2).round(0) , '\n'
	m = np.sqrt(m2).round(0)
	n = 1
	csl_factory(orientation_axis, miller, boundary_plane, m, n, grain_a, grain_b)
#	Can also just generate the symmetric grain boundaries this way?
#	grain_test = BodyCenteredCubic(directions=[[1,-1,0], [1,1,-2], [1,1,1]],#, miller=[None,[1,1,0],[1,1,1]],
#                                size=(1,1,4), symbol='Fe', pbc=(1,1,1),
#                                latticeconstant=2.83)
#	grain_b = grain_test.copy()
#	point = np.array([0.,0.,0.])
#	miller = np.array([1.,1.,1.])
#	1,1,1 plane is oriented along  xyz already
#	miller = np.array([0.,0.,1.])
#	generate_mirror(grain_b, point, miller)
#	grain_test.extend(grain_b)
#Can also just generate the symmetric grain boundaries this way?
#	grain_test = BodyCenteredCubic(directions=[[1,-1,0], [1,1,-3], [3,3,2]],#, miller=[None,[1,1,0],[1,1,1]],
#                         size=(1,1,1), symbol='Fe', pbc=(1,1,1),
#                         latticeconstant=2.83)	
#	grain_b = grain_test.copy()
#	point = np.array([0.,0.,0.])
#miller = np.array([1.,1.,1.])
#1,1,1 plane is oriented along  xyz already
#miller = np.array([0.,0.,1.])
#generate_mirror(grain_b, point, miller)
#grain_b.positions[:,2] -= 0.0
#grain_test.extend(grain_b)
#grain_test[0].position = (2.007,1.18,0.00) 
#view(grain_test)
