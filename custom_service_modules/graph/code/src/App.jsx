import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Colors,
  Legend,
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';
import autocolors from 'chartjs-plugin-autocolors';
import APIBackend from './RestAPI'

import dayjs from 'dayjs'
import weekOfYear from 'dayjs/plugin/weekOfYear';
import advancedFormat from 'dayjs/plugin/advancedFormat';


// Set up react-query
import {
  QueryClient,
  QueryClientProvider,
  useQuery
} from '@tanstack/react-query'
const queryClient = new QueryClient()

import './app.css'

dayjs.extend(weekOfYear)
dayjs.extend(advancedFormat)

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Colors,
  Legend,
  autocolors
);

function set_alpha(colour, alpha) {
  let out = colour
  // Regex to extract the numbers from a string like this "rgba(255,159,64,0.5)"
  let rgba = colour.match(/^rgba\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+[\.]?\d*)\s*\)$/i);
  if (rgba) {
    out = "rgba(" + rgba[1] + "," + rgba[2] + "," + rgba[3] + "," + alpha + ")";
  }
  else {
    let rgb = colour.match(/^rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$/i);
    if (rgb) {
      out = "rgba(" + rgb[1] + "," + rgb[2] + "," + rgb[3] + "," + alpha + ")";
    }
  }
  return out
}

//from example here: https://github.com/chartjs/Chart.js/blob/master/docs/samples/legend/events.md
function handleHover(evt, item, legend) {
  legend.chart.data.datasets.forEach((dataset, index) => {
    dataset.backgroundColor = index === item.datasetIndex ? dataset.backgroundColor : set_alpha(dataset.backgroundColor, 0.2);
    dataset.borderColor = index === item.datasetIndex ? dataset.borderColor : set_alpha(dataset.borderColor, 0.1);
  });
  legend.chart.update();
}

function handleLeave(evt, item, legend) {
  legend.chart.data.datasets.forEach((dataset) => {
    dataset.backgroundColor = set_alpha(dataset.backgroundColor, 0.5);
    dataset.borderColor = set_alpha(dataset.borderColor, 1.0);
  });
  legend.chart.update();
}


export const options = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top',
      onHover: handleHover,
      onLeave: handleLeave
    },
    tooltip: {
      callbacks: {
        label: function (context) {
          let point = context.raw;
          let series = context.dataset.label
          let label = series + " " + (point / 1000).toFixed(2) + ' kWh';
          return label;
        }
      }
    }
    // title: {
    //   display: true,
    //   text: 'Chart.js Line Chart',
    // },
  },
  interaction: {
    axis: "x",
    mode: "index",
    intersect: false,
  },
  scales: {
    y: {
      ticks: {
        // Include a dollar sign in the ticks
        callback: function (value, index, ticks) {
          return (value / 1000) + " kWh";
        }
      }
    }
  }
};

export function useConfig() {
  return useQuery(
    {
      queryKey: ['config'],
      queryFn: async () => APIBackend.api_get('http://' + document.location.host + '/config/config.json'),
      select: (data) => (data.payload)
    }
  )
}

export function useEnergyData(config) {
  let params = new URLSearchParams(window.location.search);

  let url = (config?.source?.host ? config?.source?.host : window.location.hostname) + (config?.source?.port ? ":" + config.source.port : "")
  let path = window.location.pathname

  let full_url = 'http://' + url + path + "?" + params.toString()
  console.log(full_url, !!config)

  return useQuery(
    {
      queryKey: ['data'],
      queryFn: async () => APIBackend.api_get(full_url),
      select: (data) => (data.payload),
      enabled: !!config
    }
  )
}


function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigWrapper />
    </QueryClientProvider>
  );
}

function ConfigWrapper(){
  let { data: config, isLoading: config_Loading, isError: configError, error: config_error } = useConfig()

  console.log(config)

  if (config_Loading || configError) {
    return config_error ? config_error : "Loading Config..."
  }

  return <Graph config={config}/>
}

function Graph({ config }) {
  let params = new URLSearchParams(window.location.search);
  let [type, setType] = React.useState(params.get("graph"))

  let { data, isLoading, isError, error } = useEnergyData(config)
  console.log(data, isLoading || isError, error)

  if (isLoading || isError) {
    return error ? error : "Loading..."
  }
  if (data?.buckets?.length == 0) {
    return <h1>No data to display</h1>
  }

  let graph_data = {
    labels: data.buckets,
    datasets: Object.keys(data.series).map(series_key => ({
      label: series_key,
      data: data.series[series_key],
      borderWidth: 1
    }))
  };

  console.log(type)
  return (
    <div id="frame">
      {type === "line" ?
        <Line options={options} data={graph_data} />
        : <Bar options={options} data={graph_data} />
      }
    </div>
  )
}


export default App;

