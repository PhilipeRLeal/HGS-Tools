'''
Created on 2017-12-21

This module contains meta data and access functions for GRCA well data from xls spread sheets and
database files.

@author: Andre R. Erler, GPL v3
'''

# external imports
import os
import numpy as np
import numpy.ma as ma
# internal imports
from datasets.common import days_per_month, name_of_month, getRootFolder, loadObservations
from warnings import warn
from geodata.misc import DateError, ArgumentError

## GRCA Meta-data

dataset_name = 'GRCA'
default_period = (2000,2015) # approximate data availability
root_folder = getRootFolder(dataset_name=dataset_name) # get dataset root folder based on environment variables
tsfile = dataset_name.lower()+'{0:s}_monthly.nc' # formatted NetCDF file
avgfile = dataset_name.lower()+'{0:s}_clim{1:s}.nc' # formatted NetCDF file
avgfolder = root_folder + dataset_name.lower()+'avg/' # prefix


# variable attributes and name (basically no alterations necessary...)
varatts = dict(h = dict(name='head', units='m', atts=dict(long_name='Pressure Head at Well')), # head in observation well
               # constants
               well_depth = dict(name='depth', units='m', atts=dict(long_name='Well Depth')), # well depth from surface
               wel_piezom = dict(name='d_piezo', units='m', atts=dict(long_name='Depth of Piezometer')), # where the head is measured
               screen        = dict(name='screen', units='', atts=dict(long_name='Screen Type')), 
               screen_depth  = dict(name='d_scr', units='m', atts=dict(long_name='Screen Depth')), # screen level depth...                
               screen_top    = dict(name='d_st', units='m', atts=dict(long_name='Screen Top Depth')), # ... from the surface
               screen_bottom = dict(name='d_sb', units='m', atts=dict(long_name='Screen Bottom Depth')), 
               elva_groun = dict(name='zs', units='m', atts=dict(long_name='Surface Elevation (M.S.L.)')), # surface elevation
               z_t        = dict(name='z_t', units='m', atts=dict(long_name='Screen Top Elevation (M.S.L.)')), # screen level elevation
               z_b        = dict(name='z_b', units='m', atts=dict(long_name='Screen Bottom Elevation (M.S.L.)')), # screen level elevation
               z          = dict(name='z', units='m', atts=dict(long_name='Screen/Sampling Elevation (M.S.L.)')), # elevation where the measurement is taken
               longitude  = dict(name='lon', units='deg E', atts=dict(long_name='Longitude')), # geographic longitude field
               latitude   = dict(name='lat', units='deg N', atts=dict(long_name='Latitude')), # geographic latitude field
               # axes 
               well = dict(name='well', units='', atts=dict(long_name='Well Index Number')), # well number
               time = dict(name='time', units='month', atts=dict(long_name='Month since 1979-01')),) # time coordinate
# N.B.: the time-series time offset is chose such that 1979 begins with the origin (time=0)
# list of variables to load
varlist = varatts.keys() # also includes coordinate fields    


## Functions that provide access to well-formatted PRISM NetCDF files

# pre-processed climatology files (varatts etc. should not be necessary)
def loadGRCA(name=dataset_name, well=None, period=default_period, varlist=None, varatts=None, 
             folder=avgfolder, filelist=None, lload=True):
  ''' Get the pre-processed monthly climatology of GRCA well heads as a DatasetNetCDF. '''
  # load standardized climatology dataset with GRCA-specific parameters  
  dataset = loadObservations(name=name, folder=folder, period=period, grid=None, station=None, 
                             varlist=varlist, varatts=varatts, filepattern=avgfile, filelist=filelist, 
                             lautoregrid=False, mode='climatology')
  if well:
      # identify well based on name
      well_id, well_no = getWellName(well)
      well_names = dataset.well_name[:]
      well_idx = -1      
      for i,well_name in enumerate(well_names):
          wid,wno = getWellName(well_name)
          if wid == well_id and wno == well_no:
              well_idx = i
              break
      if well_idx < 0: 
          raise ValueError(well)
      # slice out well
      dataset.load()
      dataset = dataset(well=well_idx, lidx=True)
  # return formatted dataset
  return dataset
loadGRCA_Stn = loadGRCA

# pre-processed timeseries files (varatts etc. should not be necessary)
def loadGRCA_TS(name=dataset_name, well=None, varlist=None, varatts=None, 
                folder=avgfolder, filelist=None, lload=True):
  ''' Get the pre-processed monthly timeseries for GRCA well heads as a DatasetNetCDF. '''
  # load standardized time-series dataset with GRCA-specific parameters  
  dataset = loadObservations(name=name, folder=folder, period=None, grid=None, station=None, 
                             varlist=varlist, varatts=varatts, filepattern=tsfile, filelist=filelist, 
                             lautoregrid=False, mode='climatology')
  # return formatted dataset
  return dataset
loadGRCA_StnTS = loadGRCA_TS

## Dataset API

dataset_name # dataset name
root_folder # root folder of the dataset
ts_file_pattern = None
clim_file_pattern = avgfile # filename pattern
data_folder = avgfolder # folder for user data
grid_def = None # no special name, since there is only one...
LTM_grids = [] # grids that have long-term mean data 
TS_grids = [] # grids that have time-series data
grid_res = {} # approximate resolution in degrees at 45 degrees latitude
default_grid = None
# functions to access specific datasets
loadLongTermMean = None # climatology provided by publisher
loadTimeSeries = None # time-series data
loadClimatology = loadGRCA # pre-processed, standardized climatology
loadStationClimatology = loadGRCA_Stn
loadShapeClimatology = None

## Functions that handle access to GRCA XLS/DBF files

grca_folder = os.path.join(root_folder,'GRCA Transient Waterlevels')

def getWellName(name):
  ''' helper function to break down well names into ID and number '''
  well_no = 1 # default, unless specified
  if isinstance(name,basestring):
      well = name.upper()
      if '.' in well:
          well = well.split('.')
          if len(well) == 2: well = well[0]
          elif len(well) > 2: well = '.'.join(well[:-1])
          else: raise ArgumentError 
      if '-' in well: 
          well_id,well_no = well.split('-')
          well_no = int(well_no)
      else:
          well_id = well
      if 'W' == well_id[0]:
          well_id = int(well_id[1:])
      else: 
          well_id = int(well_id)
  else: 
      well_id = int(well)
  # return components
  return well_id, well_no

# loads data from original XLS files and returns Pandas data_frame
def loadXLS(well=None, filename=None, filename_pattern='W{WELL_ID:03d}{TAG}.xlsx', folder=grca_folder, loutliers=True, sampling='M', period=(2000,2015), ltrim=False):
  # figure out filename
  if well and filename: raise ArgumentError
  elif well:
      well_id, well_no = getWellName(well)
      tag = '-{WELL_NO:d}'.format(WELL_NO=well_no) if well_no > 1 else ''
      filename = filename_pattern.format(WELL_ID=well_id, WELL_NO=well_no, TAG=tag)
  elif filename:
      well_id, well_no = getWellName(filename) 
  else: raise ArgumentError
  # local imports
  import pandas as pd
  # load data and resample to monthly
  df = pd.read_excel(os.path.join(folder, filename), sheet_name='ChartData', header=0, #skiprows=[0], 
                     index_col=None, names=None, parse_dates=True)
  # validate header
  t_label, h_label = df.columns 
  assert 'Set' in t_label, t_label
  assert 'Water Level' in h_label, h_label
  assert 'Logger' in h_label, h_label
  assert 'W' in h_label, h_label
  assert str(well_id) in h_label, h_label
  df.rename(columns={t_label:'time',h_label:'head'}, inplace=True) # rename columns
  # clean data
  df = df[np.isfinite(df['head'])] # remove NaN's
  df.drop_duplicates(subset='time', keep='first', inplace=True) # remove duplicates
  df.set_index(['time'], inplace=True, verify_integrity=True) # set time as index for aggregation
  #print(df['head']['2012-08'])
  # remove outliers
  if loutliers:
      df = df[( ( df['head'] - df['head'].mean() ) / df['head'].std() ).abs() < 3]
  # resample to monthly
  if sampling: 
      df = df.resample(sampling).mean()
  # reindex time axis
  if period:
      period = [str(p) for p in period]
      if (not ltrim) and df.index[0] < pd.to_datetime(period[0]): raise DateError(period)
      if (not ltrim) and df.index[-1] > pd.to_datetime(period[1]): raise DateError(period)
      df = df.reindex(pd.date_range(str(period[0]), str(period[1]), freq=sampling,))
  # return dataset
  return df

# function to meta data from database file
def loadMetadata(well, filename='metadata.dbf', wellname='W{WELL_ID:07d}-{WELL_NO:1d}', folder=grca_folder):
  # clean up well name
  well_id, well_no = getWellName(well)
  well = wellname.format(WELL_ID=well_id, WELL_NO=well_no)
  # open database and get relevant entry
  #from simpledbf import Dbf5
  from dbfread import DBF
  table = DBF(os.path.join(grca_folder,filename))
  meta = None
  for record in table:
      if record['PGMN_WELL'] == well: 
          meta = record.copy()
  if meta is None: 
      raise ArgumentError(well)
  # parse screen information
  screen_type,screen_depth= meta['SCREEN_HOL'].split(':')
  meta['Screen'] = screen_type.title()
  screen_hilo = []
  lunit = False
  for hilo in screen_depth.split('-'):
      if hilo[-1] == 'M':
        lunit = True 
        screen_hilo.append(float(hilo[:-1]))
      else: screen_hilo.append(float(hilo))
  if not lunit: raise ValueError(screen_depth)
  assert len(screen_hilo) == 2, screen_hilo
  meta['screen_top'] = screen_hilo[0]
  meta['screen_bottom'] = screen_hilo[1]
  meta['screen_depth'] = ( screen_hilo[0] + screen_hilo[1] ) / 2.
  meta['z']   = meta['ELVA_GROUN'] - meta['screen_depth']
  meta['z_t'] = meta['ELVA_GROUN'] - meta['screen_top']
  meta['z_b'] = meta['ELVA_GROUN'] - meta['screen_bottom']
  # return coordinate arrays (in degree)
  return meta

if __name__ == '__main__':
    
  mode = 'test_climatology'
#   mode = 'test_timeseries'
#   mode = 'convert_XLS'
#   mode = 'test_load_XLS'
  
  # do some tests
  if mode == 'test_climatology':
    
    # load climatology
    print('')
    dataset = loadGRCA(well='W178')
    print(dataset)
    print('')
    print(dataset.time)
    print(dataset.time.coord)
    print('')
    print(dataset.well_name)
    print(dataset.well_name[:])

  if mode == 'test_timeseries':
    
    # load time-series
    print('')
    dataset = loadGRCA_TS()
    print(dataset)
    print('')
    print(dataset.time)
    print(dataset.time.coord)
    print('')
    print(dataset.well_name)
    print(dataset.well_name[:])

  ## convert from XLS files to netcdf
  elif mode == 'convert_XLS': 
      
      # imports
      from glob import glob
      from geodata.base import Dataset, Axis, Variable
      from geodata.netcdf import writeNetCDF
      
      
      # load list if well files and generate list of wells
      well_files = glob(os.path.join(grca_folder,'W*.xlsx'))
      well_files.sort()
      wells = [os.path.basename(name[:-5]) for name in well_files]
      print(wells)
      
      # dataset
      period = default_period
      time_ax = Axis(coord=np.arange(12*(period[1]-period[0]))+252, **varatts['time']) # origin: 1979-01
      well_ax = Axis(coord=np.arange(len(wells))+1, name='well', units='') 
      dataset = Dataset(name='grca', title='GRCA Observation Wells')
      # add meta data
      meta_dicts = [loadMetadata(well) for well in wells]
      for key in meta_dicts[0].keys():
          if key in varatts: atts = varatts[key]
          elif key.lower() in varatts: atts = varatts[key.lower()]
          else: atts = dict(name=key, units='')
          if atts['units']: data = np.asarray([wmd[key] for wmd in meta_dicts], dtype=np.float64)
          else: data = np.asarray([wmd[key] for wmd in meta_dicts])
          dataset += Variable(data=data, axes=(well_ax,), **atts)
      # add names
      dataset += Variable(data=wells, axes=(well_ax,), name='well_name', units='', 
                          atts=dict(long_name='Short Well Name'))
      for varname in ('d_piezo','well_name','depth'):
          print('')
          print(dataset[varname])
          print(dataset[varname][:])      
      # add well heads
      data = np.zeros((len(well_ax),len(time_ax),)) # allocate array
      # load data for wells...
      print('\nLoading Well Data:')
      for i,well_file in enumerate(well_files):
          print('  '+wells[i])
          df = loadXLS(filename=os.path.basename(well_file), folder=os.path.dirname(well_file), 
                       loutliers=True, sampling='M', period=period, ltrim=False)
          data[i,:] = df['head']
      # add head variable
      dataset += Variable(data=data, axes=(well_ax,time_ax), **varatts['h'])
      
      # write dataset to disk
      # timeseries
      print(''); print(dataset); print('')
      filepath = os.path.join(avgfolder,tsfile.format('',))
      writeNetCDF(dataset, ncfile=filepath, feedback=True)
      # climatology
      clim_ds = dataset.climMean()
      print(''); print(clim_ds); print('')      
      filepath = os.path.join(avgfolder,avgfile.format('','_{}-{}'.format(*period)))
      writeNetCDF(clim_ds, ncfile=filepath, feedback=True)

  ## test load function for XLS files
  elif mode == 'test_load_XLS': 

#     # load Metadata
#     meta = loadMetadata(well='W178', )
#     # inspect dictionary
#     for item in meta.items(): print(item)
  
      # load timeseries data from XLS files
      data = loadXLS(well='W347-3')
      # inspect data
      print(data)
