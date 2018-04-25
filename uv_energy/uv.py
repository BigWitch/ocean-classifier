# Extract mean daily u/v data from ROMS

print('Getting temperature and salinity daily means...')

# import modules
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
import math
import matplotlib.pyplot as plt
import pylab
import matplotlib.cm as cm
from mpl_toolkits.basemap import Basemap # basemap tools
import argparse
import datetime
from datetime import datetime, timedelta # for working with datetimes
from netCDF4 import Dataset # reads netCDF file
from os import listdir
from os.path import isfile, join
from itertools import compress # for filteriung using boolean masks
import sys

# __Setup__

# How many NetCDF files to use (set the range)
start = 0
end = 277 # for 277 files (zero index but range() does not include last number)

# set range for data to collect
# updated to 200km from 50km on 20th of March 2018
xmin = 149.111697
xmax = 151.342103
ymin = -37.151332
ymax = -35.352688

# depth mask
depth_mask = 200

# add to list witout append
def add(lst, obj, index): return lst[:index] + [obj] + lst[index:]

# for getting time data
def grab_sst_time(time_idx):
    """
    gets datetime object for sst map projection
    """
    dtcon_days = time[time_idx]
    dtcon_start = datetime(1990,1,1) # This is the "days since" part
    dtcon_delta = timedelta(dtcon_days/24/60/60) # Create a time delta object from the number of days
    dtcon_offset = dtcon_start + dtcon_delta # Add the specified number of days to 1990
    frame_time = dtcon_offset
    return frame_time

def grab_data(time_idx):
	# make frame__idx an integer to avoid slicing errors
    frame_idx = int(time_idx)
    # get 'frame_time'
    frame_time = grab_sst_time(frame_idx)

    # Get data for entire range
    u = fh.variables['u'][frame_idx,29,:,:] 
    v = fh.variables['v'][frame_idx,29,:,:]
    # remove masks
    u = np.ma.filled(u.astype(float), np.nan)
    v = np.ma.filled(v.astype(float), np.nan)

    # entire range mean
    full_u_proto = np.nanmean(u)
    full_v_proto = np.nanmean(v)
    # mont range
    mont_u_proto = np.nanmean(u[eta_rho,xi_rho])
    mont_v_proto = np.nanmean(v[eta_rho,xi_rho])
    # bath range
    bath_u_proto = np.nanmean(u[eta_rho_bath,xi_rho_bath])
    bath_v_proto = np.nanmean(v[eta_rho_bath,xi_rho_bath])

    return full_u_proto, full_v_proto, mont_u_proto, mont_v_proto, bath_u_proto, bath_v_proto, frame_time 

# __Setup_subsets__

# get list of files in data directory
in_directory = "/Users/lachlanphillips/PhD_Large_Data/ROMS/Montague_subset"
file_ls = [f for f in listdir(in_directory) if isfile(join(in_directory, f))]
file_ls = list(filter(lambda x:'naroom_avg' in x, file_ls))
file_ls = sorted(file_ls)

# get lats and lons
nc_file = in_directory + '/' + file_ls[0]
fh = Dataset(nc_file, mode='r')
lats = fh.variables['lat_rho'][:] 
lons = fh.variables['lon_rho'][:]
bath = fh.variables['h'][:]
# combine to list of tuples
point_tuple = zip(lats.ravel(), lons.ravel(), bath.ravel())
point_list = []
point_list_bath = []

j = 0
# iterate over tuple points and keep every point that is in box and above depth mask
for i in point_tuple:
    if ymin <= i[0] <= ymax and xmin <= i[1] <=xmax:
        point_list.append(j)
    j = j + 1

# make point list into tuple list of array coordinates
eta_rho = []
xi_rho = []
for i in point_list:
    eta_rho.append(int(i/165))
    xi_rho.append(int(i%165))

# reset iterateor
point_tuple = zip(lats.ravel(), lons.ravel(), bath.ravel())

j = 0
# iterate over tuple points and keep every point that is in box and above depth mask
for i in point_tuple:
    if ymin <= i[0] <= ymax and xmin <= i[1] <=xmax and i[2] < depth_mask:
        point_list_bath.append(j)
    j = j + 1

# make point list into tuple list of array coordinates
eta_rho_bath = []
xi_rho_bath = []
for i in point_list_bath:
    eta_rho_bath.append(int(i/165))
    xi_rho_bath.append(int(i%165))

# __Main_Program__

# lists to collect data
full_u = []
full_v = []
mont_u = []
mont_v = []
bath_u = []
bath_v = []
xtime = []

# get data for each file (may take a while)
for i in range(start, end):
    # import file
    nc_file = in_directory + '/' + file_ls[i]
    fh = Dataset(nc_file, mode='r')
    print('Extracting data from file: '+file_ls[i]+' | '+str(i+1)+' of '+ str(len(file_ls)))
    # fname = str(file_ls[i])[11:16]

    # extract time
    time = fh.variables['ocean_time'][:]

    # get data
    for i in range(0, len(time)):
        full_u_proto, full_v_proto, mont_u_proto, mont_v_proto, bath_u_proto, bath_v_proto, xtime_proto = grab_data(i)
        full_u, full_v = add(full_u, full_u_proto, i), add(full_v, full_v_proto, i)
        mont_u, mont_v = add(mont_u, mont_u_proto, i), add(mont_v, mont_v_proto, i)
        bath_u, bath_v = add(bath_u, bath_u_proto, i), add(bath_v, bath_v_proto, i)
        xtime = add(xtime, xtime_proto, i)
    # close file
    fh.close()

# make dataframe from ratio metric lists
out_df  = {'xtime': xtime, 'full_u': full_u, 'full_v': full_v,
			'mont_u': mont_u, 'mont_v': mont_v, 'bath_u': bath_u,
			'bath_v': bath_v}
out_df = pd.DataFrame(data=out_df)
out_df = out_df.drop_duplicates('xtime')
out_df = out_df.sort_values('xtime').reset_index(drop=True)
print(out_df)

# save to csv
print('_____Please_Wait_____')
print('Writing ocean data to file...')
dt = datetime.now()
dt = dt.strftime('%Y%m%d-%H%M')
output_fn = './output/' + 'u-v_' + str(start).zfill(3) + '-' + str(end).zfill(3) + '_' + dt + '.csv' 
out_df.to_csv(output_fn, index=False)

print('_____Program_End_____')
