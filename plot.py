import pandas as pd
import numpy as np
import re 
import io
import requests
import matplotlib.pyplot as plt

def download(url):
    s = requests.get(url).content
    return pd.read_csv(io.StringIO(s.decode('utf-8')))

# use the 'seaborn-colorblind' style
plt.style.use('seaborn-colorblind')

#source: https://data.humdata.org/dataset/5dff64bc-a671-48da-aa87-2ca40d7abf02
url_confirmed="https://data.humdata.org/hxlproxy/api/data-preview.csv?url=https%3A%2F%2Fraw.githubusercontent.com%2FCSSEGISandData%2FCOVID-19%2Fmaster%2Fcsse_covid_19_data%2Fcsse_covid_19_time_series%2Ftime_series_covid19_confirmed_global.csv&filename=time_series_covid19_confirmed_global.csv"
url_deaths = "https://data.humdata.org/hxlproxy/api/data-preview.csv?url=https%3A%2F%2Fraw.githubusercontent.com%2FCSSEGISandData%2FCOVID-19%2Fmaster%2Fcsse_covid_19_data%2Fcsse_covid_19_time_series%2Ftime_series_covid19_deaths_global.csv&filename=time_series_covid19_deaths_global.csv"
url_recovered = "https://data.humdata.org/hxlproxy/api/data-preview.csv?url=https%3A%2F%2Fraw.githubusercontent.com%2FCSSEGISandData%2FCOVID-19%2Fmaster%2Fcsse_covid_19_data%2Fcsse_covid_19_time_series%2Ftime_series_covid19_recovered_global.csv&filename=time_series_covid19_recovered_global.csv"

#obtaining data frames from urls
confirmed = download(url_confirmed)
death =  download(url_deaths)
recovered = download(url_recovered)

#Updated on
date = pd.to_datetime(death.columns[-1]).strftime("%B %d, %Y")

#source: https://datahub.io/JohnSnowLabs/country-and-continent-codes-list#python
country_list = pd.read_csv('country-and-continent-codes-list-csv_csv.csv')

#data cleaning
mappings = {'Kyrgyzstan': 'Kyrgyz Republic', 
 'Laos':'Lao People\'s Democratic Republic',
 'Libya' :'Libyan Arab Jamahiriya', 
 'Burma': 'Myanmar', 
 'Brunei': 'Brunei Darussalam', 
 'Czechia' : 'Czech Republic', 
 'US': 'United States of America', 
 'Cabo Verde' : 'Cape Verde', 
 'North Macedonia' : 'Macedonia',
 'United Kingdom' : 'United Kingdom of Great Britain & Northern Ireland',
 'West Bank and Gaza' : 'Palestinian Territory', 
 'Syria':'Syrian Arab Republic', 
 'Russia':'Russian Federation'}

def merge_continent_data(confirmed):
    #Removing North Korea because there is no COVID-19 data.
    country_list.drop(country_list.where(country_list.Country_Name == 'Korea, Democratic People\'s Republic of').dropna().index, inplace=True)
    
    country_list['Country_Name'] = country_list['Country_Name'].apply(lambda s : re.sub("((, .*)|( \(.*))", "", str(s)))
    country_list.rename({'Continent_Name': 'Continent'}, axis='columns', inplace=True)
    confirmed.rename({'Country/Region': 'Country'}, axis='columns', inplace=True)

    #Deciding continent on countries belonging to two continents to avoid duplicates. 
    country_list.drop(country_list.where(country_list.Country_Name == 'Turkey').where(country_list.Continent == 'Europe').dropna().index, inplace=True)
    country_list.drop(country_list.where(country_list.Country_Name == 'Russian Federation').where(country_list.Continent == 'Asia').dropna().index, inplace=True)
    
    confirmed['Country'] = confirmed['Country'].apply(lambda s: re.sub('((, .*)|( \(.*))|\*', '', s))
    confirmed['Country'] = confirmed['Country'].apply(lambda s: mappings[s] if s in mappings else s)
    
    confirmed = confirmed.groupby('Country').sum()

    #Missing 2 cruis ship ('MS Zaandam','Diamond Princess'), 'Eswatini', 'Kosovo' 
    conf_cont = pd.merge(country_list,confirmed, left_on='Country_Name', right_index=True, how='inner')
    
    conf_cont.drop(['Continent_Code',
       'Two_Letter_Country_Code', 'Three_Letter_Country_Code',
       'Country_Number', 'Lat', 'Long'], axis='columns', inplace=True)
    
    conf_cont.rename({'Country_Name': 'Country'}, axis='columns', inplace=True)
    
    conf_cont.set_index(['Continent', 'Country'], inplace=True)
    
    conf_cont.columns = list(map(lambda x: pd.to_datetime(x).strftime("%b-%d"), conf_cont.columns))

    return conf_cont

#Merged data frames
confirmed_df = merge_continent_data(confirmed)
death_df = merge_continent_data(death)
recovered_df = merge_continent_data(recovered)

#Data frames by Continent
conf_cont = confirmed_df.groupby(['Continent']).sum()
death_cont = death_df.groupby(['Continent']).sum()
recov_cont = recovered_df.groupby(['Continent']).sum()

active_cont = conf_cont - death_cont - recov_cont
death_rate_cont = 100*death_cont/(death_cont+recov_cont)

continent = 'Asia'
min_total = 15000

#Data frames for countries in Asia with more than min_total cases confirmed.
confirmed_asia = confirmed_df.loc[continent]
confirmed_asia = confirmed_asia.where(confirmed_asia[confirmed_asia.columns[-1]] > min_total).dropna()

deaths_asia = death_df.loc[continent]
deaths_asia = deaths_asia[deaths_asia.index.isin(confirmed_asia.index)]

recovered_asia = recovered_df.loc[continent]
recovered_asia = recovered_asia[recovered_asia.index.isin(confirmed_asia.index)]

death_rate_asia = 100*deaths_asia/(recovered_asia + deaths_asia)
active_asia = confirmed_asia - recovered_asia - deaths_asia

# use gridspec to partition the figure into subplots
import matplotlib.gridspec as gridspec

def plot_deaths_grid(subplt, data, percentage=False, spacing=0):
    series = data[data.columns[-1]].sort_values()
    xvals = list(map(lambda x : "S.Arabia" if x == "Saudi Arabia" else re.sub(" ", "\n", x), series.index))
    vals = series.values
    bars = subplt.bar(xvals, vals, width = 0.6, color='lightslategrey')
    
    if percentage:
        f = lambda x : '{:.2f}%'.format(x)
    else:
        f = int        
    i = np.argmax(vals)
    bars[i].set_color('darkred')
    for bar in bars:
        height = bar.get_height()
        subplt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + spacing,  f(height), 
                     ha='center', color='black', fontsize=8)

    # remove the frame of the chart
    for spine in subplt.spines.values():
        spine.set_visible(False)

    subplt.get_yaxis().set_visible(False)
    plt.xticks(fontsize=7)
    
    for tick in subplt.get_xaxis().get_ticklabels():
        tick.set_rotation(45)
    
    return fig, bars

plt.rcParams.update({'font.size': 8})

fig = plt.figure(figsize=(10,6))
gspec = gridspec.GridSpec(3, 4,hspace=0.3)

g_death = plt.subplot(gspec[2,0:1])
a_death = plt.subplot(gspec[2,1:2])
g_rate  = plt.subplot(gspec[2, 2:3])
a_rate = plt.subplot(gspec[2,3:4])
g_active = plt.subplot(gspec[0:2, 0:2])
a_active = plt.subplot(gspec[0:2, 2:4])

plot_deaths_grid(a_rate, death_rate_asia, percentage=True, spacing=0.4)
plot_deaths_grid(a_death, deaths_asia, spacing=80)
ax = (active_asia/1000).transpose().plot(ax=a_active)
ax.legend(loc='upper left', prop={'size': 8})
ax.yaxis.set_label_position("right")
ax.yaxis.tick_right()
ax.spines['left'].set_visible(False)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.set_ylabel('Active cases in {} (thousands)\n [Countries that have more than {} total cases]'.format(continent,min_total))

plot_deaths_grid(g_death, death_cont, spacing=1500)
plot_deaths_grid(g_rate, death_rate_cont, percentage=True, spacing=0.6)
ax = (active_cont/1000).transpose().plot(ax=g_active)
ax.legend(prop={'size': 8})
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.spines['top'].set_visible(False)

ax.set_ylabel('Active cases worldwide (thousands)')

plt.suptitle('COVID-19: Understanding current situation in {} as of {}.'.format(continent, date), y=0.92)

fig.text(.32, .02, 'Total number of deaths', ha='center')
fig.text(.72, .02, 'Death rate (closed cases)', ha='center')
fig.text(.85, .005, 'Designed by @ezecastellano', ha='center', alpha=0.6)

# resize the figure to match the aspect ratio of the Axes    
fig.set_size_inches(12, 9, forward=True)

fig.savefig('covid19-asia.png')





