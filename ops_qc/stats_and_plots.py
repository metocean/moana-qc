import os
import re
import logging       
import simplekml
import numpy as np
import pandas as pd
import xarray as xr
import seawater as sw
import datetime as dt
from glob import glob
from erddapy import ERDDAP
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from ops_qc.utils import load_yaml
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from cartopy.mpl.gridliner import LATITUDE_FORMATTER, LONGITUDE_FORMATTER
import itertools
xr.set_options(keep_attrs=True)

# cycle_dt = dt.datetime.utcnow()

class Wrapper(object):
    """
    Wrapper class for publication of observational data onto THREDDS servers.
    Takes a list of quality-controlled netcdf files and reformats the ones available
    for public access using CF-1.6 conventions and following IMOS and ARGOS conventions
    IMOS: https://s3-ap-southeast-2.amazonaws.com/content.aodn.org.au/Documents/IMOS/Conventions/IMOS_NetCDF_Conventions.pdf
    ARGOS: https://archimer.ifremer.fr/doc/00187/29825/94819.pdf

    Arguments:
        filelist -- list of files to apply transformation to
        outfile_ext -- extension to add to filenames when saving as netcdf files
        out_dir - directory to save public netcdf files (to send to THREDDS server)
        qc_class -- python class wrapper for running qc tests, returns updated xarray dataset
            that includes qc flags and updated status_file
        attr_file -- location of attribute_list.yml, default uses the one in the python
            package, should be a yaml file (see sample one in ops_qc directory)

    """
    
    def __init__(
        self,
        data_dir="/data/obs/mangopare/processed/",
        out_dir="/data/obs/mangopare/weekly_stats/%Y%m%d_00z/",
        bbox=[161, 190, -52, -31],
        resolution=1,
        lon_offset=180,
        bounds=[0,2,4,8,12,16,24,28],
        kml_output="mangopare_deployments_%Y%m%d.kml",
        **kwargs,
    ):
        self.data_dir = data_dir
        self.out_dir = out_dir
        self.logger = logging
        self.files = glob(os.path.join(self.data_dir, "*.nc"))
        self.bbox = bbox
        self.resolution = resolution
        self.lon_offset = lon_offset
        self.bounds = bounds
        self.kml = simplekml.Kml()
        self.kml_output = kml_output

        self.x_edges = np.arange(self.bbox[0] - self.resolution, self.bbox[1] + self.resolution, self.resolution)
        self.y_edges = np.arange(self.bbox[2] - self.resolution, self.bbox[3] + self.resolution, self.resolution)
    
    def set_environment(self):
        """Create output directories."""
        self.logger.info("--- Creating directories")
        if not os.path.isdir(self.cycle_dt.strftime(self.out_dir)):
            os.makedirs(self.cycle_dt.strftime(self.out_dir))
    
    def set_cycle(self, cycle_dt):
        self.cycle_dt = cycle_dt
        self.outdir = cycle_dt.strftime(self.outdir)
        self.week_end = cycle_dt.replace(minute=0, second=0, microsecond=0)
        self.week_start = self.week_end - dt.timedelta(days=7)

    def find_files_in_date_range(self):
        """
        Find files in the directory matching MOANA_####_###_YYMMDDHHMMSS_qc.n pattern within the date range [start_dt, end_dt].
        Args:
            directory (str): Directory to search.
            start_dt (datetime): Start datetime (inclusive).
            end_dt (datetime): End datetime (inclusive).
        Returns:
            list: List of file paths within the date range.
        """

        pattern = re.compile(r"MOANA_\d{4}_\d{3}_(\d{10,12})_qc\.n")
        files_in_range = []
        for fname in os.listdir(self.data_dir):
            match = pattern.match(fname)
            if match:
                date_str = match.group(1)
                # Try to parse as YYMMDDHHMMSS or YYMMDDHHMM
                file_dt = None
                for fmt in ("%y%m%d%H%M%S", "%y%m%d%H%M"):
                    try:
                        file_dt = dt.datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue
                if file_dt and self.week_start <= file_dt <= self.week_end:
                    files_in_range.append(os.path.join(self.data_dir, fname))
        return files_in_range
    
    def separate_files_by_public(self, files):
        public_files = []
        private_files = []
        for f in files:
            ds = xr.open_dataset(f)
            # Get the 'public' attribute, which may be a string
            is_public = getattr(ds, 'public', False)
            # Convert string to boolean if needed
            if isinstance(is_public, str):
                is_public = is_public.lower() == 'true'
            if is_public:
                public_files.append(f)
            else:
                private_files.append(f)
        return public_files, private_files
    
    def calc_grid_hist(self, x_coords, y_coords, time, x_edges, y_edges):
        """Takes x,y (e.g., lon, lat) coordinates of each profile or 
        sensor deployment and calculates the average monthly number 
        of profiles/deployments per grid cell.  Grid cells are defined 
        by x_edges and y_edges (e.g., longitude and latitude coordinates).  

        Parameters
        ----------
        x_coords : np.array
            Measurements' x_coordinates (e.g., longitude)
        y_coords : np.array
            Measurements' y_coordinates (e.g., latitude)
        time : np.array
            Measurements' times
        x_edges : list
            x-coordinates of grid cell edges
        y_edges : list
            y-coordinates of grid cell edges

        Returns
        -------
        tuple[list, list, list]
            Returns average monthly counts per grid cell (h) and grid
            cell centers (x,y), i.e. (lon,lat)
        """
        df = (
            pd.DataFrame(data={"xc": x_coords, "yc": y_coords, "time": pd.to_datetime(time)})
            .drop_duplicates()
            .set_index("time")
        )

        x2 = []
        y2 = []
        h2 = []

        for xa, ya in itertools.product(x_edges, y_edges):
            yb = ya + self.resolution
            xb = xa + self.resolution
            in_cell = df.loc[
                (df.yc >= ya) & (df.yc < yb) & (df.xc >= xa) & (df.xc < xb)
                ].dropna()
            ctm = in_cell.resample("MS")["yc"].count().fillna(0).mean()
            x2.append((xa + xb) / 2)
            y2.append((ya + yb) / 2)
            h2.append(ctm)

        x = np.array(x2)
        y = np.array(y2)
        h = np.array(h2)

        return h, x, y

    def obtain_info(self, filelist):
        """"
        Returns
        -------
        tuple[pd.DataFrame, dict, list]
            Returns a dataframe of the initial latitude, longitude, sensor ID
            and time of each deployment.
        """

        lat = []
        lon = []
        deploy_time = []
        sensor_ids = []

        for file in filelist:
            ds = xr.open_dataset(file)
            mask = ds["QC_FLAG"] < 4
            ds = ds.where(mask, drop=True)
            if len(ds.LATITUDE) < 1:
                ds.close()
                continue
            lat.append(float(ds.LATITUDE[0]))
            lon.append(float(ds.LONGITUDE[0]))
            deploy_time.append(ds.TIME[0].values)
            sensor_id = ds.attrs.get("moana_serial_number", "NA")
            sensor_ids.append(sensor_id)
            ds.close()

        df = pd.DataFrame({"lat": lat, "lon": lon, "time": deploy_time, "sensor_id": sensor_ids}).dropna()
        df['time'] = df['time'].dt.tz_localize('UTC')
        return df

    def download_erddap(
            url,
            dataset_id,
            start_time,
            end_time,
            lon_min,
            lon_max,
            lat_min,
            lat_max,
            variables,
    ):
        """Connects to ERDDAP, loads geospatial data into a pandas dataframe with
        time as the index.  Note that often you may need to query across a longitude
        of -180 using two separate queries using different lon_min and lon_max.

        Parameters
        ----------
        url : str
            ERDDAP url, for example, "http://www.ifremer.fr/erddap"
        dataset_id : str
            Comes from the particular ERDDAP server's documentation/metadata
        start_time : str
            Start of time range for query in format '%Y-%m-%dT%H:%M:%S'
        end_time : str
            End of time range for query in format '%Y-%m-%dT%H:%M:%S'
        lon_min : float
        lon_max : float
        lat_min : float
        lat_max : float
        variables : list
            Variables to return from ERDDAP query, example, ['latitude','longitude',
            'time','instrument_serial_number','depth','temp','qc_flag']

        Returns
        -------
        pd.DataFrame
            Pandas dataframe containing the variables in variable_list as columns and with time as the index
        """
        e = ERDDAP(server=url, protocol="tabledap")
        e.response = "nc"
        e.dataset_id = dataset_id
        e.variables = variables
        e.constraints = {
            "latitude>=": lat_min,
            "latitude<=": lat_max,
            "longitude>=": lon_min,
            "longitude<=": lon_max,
            "time>=": start_time,
            "time<=": end_time,
        }
        df = e.to_pandas(parse_dates=["time (UTC)"], index_col="time (UTC)").dropna()
        return df

    def load_argo(self, url="http://www.ifremer.fr/erddap", dataset_id = "ArgoFloats", variables = ["latitude", "longitude", "time", "float_serial_no", "pres"]):
        dmin = self.week_start.strftime("%Y-%m-%dT%H:%M:%S")
        dmax = self.week_end.strftime("%Y-%m-%dT%H:%M:%S")

        # Reformat "box" for use with ERDDAP, i.e. break into
        # two boxes on either side of the international dateline
        # if needed.
        if self.box[1] > 180:
            box1 = list(self.box)
            box2 = list(self.box)
            box1[1] = 180
            box2[0] = -180
            box2[1] = (self.box[1] + 180) % 360 - 180
        else:
            box1 = self.box
            box2 = False

        # one side of the international date line
        argo = self.download_erddap(
            url,
            dataset_id,
            start_time=dmin,
            end_time=dmax,
            lon_min=box1[0],
            lon_max=box1[1],
            lat_min=box1[2],
            lat_max=box1[3],
            variables=variables,
        )

        # other side of the international date line, if needed
        if box2:
            argo_1 = self.download_erddap(
                url,
                dataset_id,
                start_time=dmin,
                end_time=dmax,
                lon_min=box2[0],
                lon_max=box2[1],
                lat_min=box2[2],
                lat_max=box2[3],
                variables=variables,
            )

            # put the two sides of the international date line together
            argo = pd.concat([argo, argo_1])
            argo = argo.rename(
                columns={
                    "latitude (degrees_north)": "lat",
                    "longitude (degrees_east)": "lon",
                }
            )

            #convert longitude to 0-360
            argo["lon"] = argo["lon"] % 360
        return argo

    def generate_spatial_map_plot(self, argo_h, argo_x, argo_y,
                                mangopare_h, mangopare_x, mangopare_y,
                                filename):
        # plot parameters
        ms = 38
        bounds = [0, 4, 8, 12, 16, 24, 28]
        plt.rcParams.update(plt.rcParamsDefault)
        # Set up plots
        fig, (ax0, ax1) = plt.subplots(nrows=1, ncols=2,
                                    subplot_kw={'projection': ccrs.PlateCarree(central_longitude=self.lon_offset)},
                                    figsize=(9, 6), dpi=120, facecolor='w', edgecolor='k')
        ## Panel 1
        # plot Argo data
        colors = plt.get_cmap('Blues')(np.linspace(0, 1, len(bounds) + 1))
        cmap = mcolors.ListedColormap(colors[1:-1])
        cmap.set_over(colors[-1])
        cmap.set_under(colors[0])
        norm = mcolors.BoundaryNorm(boundaries=bounds, ncolors=len(bounds) - 1)
        sc2 = ax0.scatter(argo_x + self.lon_offset, argo_y, c=argo_h, s=ms, marker='s', cmap=cmap, norm=norm)
        ax0.plot([self.box[0], self.box[0], self.box[1], self.box[1]], [self.box[2], self.box[3], self.box[3], self.box[2]])
        cb = plt.colorbar(sc2, ax=ax0, extend='both', orientation='horizontal', pad=0.1)
        cb.set_label('Number of Argo profiles')
        # plot properties
        ax0.set_extent(self.box, crs=ccrs.PlateCarree())
        ax0.coastlines(resolution='10m', facecolor='grey')
        land_10m = cfeature.NaturalEarthFeature('physical', 'land', '10m', edgecolor='black', facecolor=cfeature.COLORS['land'])
        ax0.add_feature(land_10m)
        gl = ax0.gridlines(crs=ccrs.PlateCarree(), draw_labels=True,
                        linewidth=0, color='gray', alpha=0.5, linestyle='--')
        gl.top_labels = False
        gl.xlines = True
        gl.xlocator = mticker.FixedLocator(range(-180, 180, 5))
        gl.xformatter = LONGITUDE_FORMATTER
        gl.yformatter = LATITUDE_FORMATTER
        gl.xlabel_style = {'size': 15, 'color': 'black'}
        gl.xlabel_style = {'color': 'black'}
        ## Panel 2
        # plot Argo data
        colors = plt.get_cmap("Blues")(np.linspace(0, 1, len(bounds) + 1))
        cmap = mcolors.ListedColormap(colors[1:-1])
        cmap.set_over(colors[-1])
        cmap.set_under(colors[0])
        norm = mcolors.BoundaryNorm(boundaries=bounds, ncolors=len(bounds) - 1)
        sc2 = ax1.scatter(
            argo_x + self.lon_offset, argo_y, c=argo_h, s=ms, marker="s", cmap=cmap, norm=norm
        )
        # plot Mangopare data
        colors = plt.get_cmap("Oranges")(np.linspace(0, 1, len(bounds) + 1))
        cmap = mcolors.ListedColormap(colors[1:-1])
        cmap.set_over(colors[-1])
        cmap.set_under(colors[0])
        norm = mcolors.BoundaryNorm(boundaries=bounds, ncolors=len(bounds) - 1)
        sc = ax1.scatter(mangopare_x + self.lon_offset, mangopare_y, c=mangopare_h, s=ms, marker="s", cmap=cmap, norm=norm)
        ax1.plot([self.box[0], self.box[0], self.box[1], self.box[1]], [self.box[2], self.box[3], self.box[3], self.box[2]])

        # Colorbars
        cb = plt.colorbar(sc, ax=ax1, extend="both", orientation="horizontal", pad=0.1)
        cb.set_label(r"Number of Mangōpare deployments")
        # plot properties
        ax1.set_extent(self.box, crs=ccrs.PlateCarree())
        ax1.coastlines(resolution="10m", facecolor="grey")
        land_10m = cfeature.NaturalEarthFeature(
            "physical", "land", "10m", edgecolor="black", facecolor=cfeature.COLORS["land"]
        )
        ax1.add_feature(land_10m)

        gl = ax1.gridlines(
            crs=ccrs.PlateCarree(),
            draw_labels=True,
            linewidth=0,
            color="gray",
            alpha=0.5,
            linestyle="--",
        )
        gl.top_labels = False
        gl.xlines = True
        gl.xlocator = mticker.FixedLocator(range(-180, 180, 5))
        gl.xformatter = LONGITUDE_FORMATTER
        gl.yformatter = LATITUDE_FORMATTER
        gl.xlabel_style = {"size": 15, "color": "black"}
        gl.xlabel_style = {"color": "black"}
        fig.savefig(filename, dpi=300, bbox_inches="tight")
        plt.close(fig)

    def generate_kml_file(self, df, output_filename=None):
        for _, row in df.iterrows():
            self.kml.newpoint(
                name = str(row['sensor_id']),
                coords = [(row['lon'], row['lat'])]
            )
        self.kml.save(self.cycle_dt.strftime(output_filename))

    def run(self):
        self.set_cycle()
        files = self.find_files_in_date_range()
        self.logger.info(f"--- Found {len(files)} files in date range")
        if len(files) == 0:
            self.logger.info("--- No files to process, exiting")
            return
        self.set_environment()
        self.logger.info("--- Separating public and private files")
        public_files, private_files = self.separate_files_by_public(files)
        df_public = self.obtain_info(public_files)
        public_h, public_x, public_y = self.calc_grid_hist(
                                        x_coords=df_public['lon'].values,
                                        y_coords=df_public['lat'].values,
                                        time=df_public['time'].values,
                                        x_edges=self.x_edges,
                                        y_edges=self.y_edges,
                                    )
        df_private = self.obtain_info(private_files)
        private_h, private_x, private_y = self.calc_grid_hist(
                                        x_coords=df_private['lon'].values,
                                        y_coords=df_private['lat'].values,
                                        time=df_private['time'].values,
                                        x_edges=self.x_edges,
                                        y_edges=self.y_edges,
                                    )
        self.logger.info("--- Downloading Argo data from ERDDAP")
        df_argo = self.load_argo()
        argo_h, argo_x, argo_y = self.calc_grid_hist(
                                        x_coords=df_argo['lon'].values,
                                        y_coords=df_argo['lat'].values,
                                        time=df_argo.index.values,
                                        x_edges=self.x_edges,
                                        y_edges=self.y_edges,
                                    )
        private_plot_filename = os.path.join(
            self.outdir,
            f"private_mangopare_{self.week_start.strftime('%Y%m%d')}_{self.week_end.strftime('%Y%m%d')}"
        )
        public_plot_filename = os.path.join(
            self.outdir,
            f"public_mangopare_{self.week_start.strftime('%Y%m%d')}_{self.week_end.strftime('%Y%m%d')}"
        )
        self.logger.info("--- Generating spatial private data map plot")
        self.generate_spatial_map_plot(
            argo_h, argo_x, argo_y,
            private_h, private_x, private_y,
            private_plot_filename+".png"
        )
        self.logger.info("--- Generating spatial public data map plot")
        self.generate_spatial_map_plot(
            argo_h, argo_x, argo_y,
            public_h, public_x, public_y,
            public_plot_filename
        )
        self.logger.info("--- Generating public data kml file")
        self.generate_kml_file(df_public, output_filename=public_plot_filename+".kml")
        self.logger.info("--- Generating private data kml file")
        self.generate_kml_file(df_private, output_filename=private_plot_filename+".kml")
        self.logger.info("--- Finished processing")