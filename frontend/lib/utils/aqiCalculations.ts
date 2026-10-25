// AQI Calculations and Color Utilities

export interface AQIInfo {
  level: string;
  color: string;
  message: string;
  category: string;
}

export const AQI_SCALE: Record<string, AQIInfo> = {
  good: {
    level: 'Good',
    color: '#00B050',
    message: 'Air quality is satisfactory',
    category: '0-50',
  },
  satisfactory: {
    level: 'Satisfactory',
    color: '#92D050',
    message: 'Acceptable air quality',
    category: '51-100',
  },
  moderate: {
    level: 'Moderate',
    color: '#FFFF00',
    message: 'Sensitive groups be careful',
    category: '101-200',
  },
  poor: {
    level: 'Poor',
    color: '#FF6600',
    message: 'Avoid prolonged outdoor exposure',
    category: '201-300',
  },
  veryPoor: {
    level: 'Very Poor',
    color: '#FF0000',
    message: 'Respiratory discomfort likely',
    category: '301-400',
  },
  severe: {
    level: 'Severe',
    color: '#7030A0',
    message: 'Stay indoors. Wear N95 mask',
    category: '401+',
  },
};

export function getAQIInfo(pm25: number): AQIInfo {
  if (pm25 <= 50) return AQI_SCALE.good;
  if (pm25 <= 100) return AQI_SCALE.satisfactory;
  if (pm25 <= 200) return AQI_SCALE.moderate;
  if (pm25 <= 300) return AQI_SCALE.poor;
  if (pm25 <= 400) return AQI_SCALE.veryPoor;
  return AQI_SCALE.severe;
}

export function getHealthAdvice(pm25: number): string {
  if (pm25 < 60)
    return 'Air quality will be Good. Safe for all outdoor activities.';
  if (pm25 < 90)
    return 'Air quality will be Moderate. Sensitive groups should limit outdoor time.';
  if (pm25 < 120)
    return 'Air quality will be Poor. Avoid prolonged outdoor exposure.';
  if (pm25 < 200)
    return 'Air quality will be Very Poor. Wear a mask outdoors.';
  return 'Air quality will be Severe. Stay indoors. Wear N95 mask if going out.';
}

export function getPollutantExplanation(
  pollutant: string
): string {
  const explanations: Record<string, string> = {
    PM10: 'Dust from roads, construction sites, and vehicle tyres',
    CO: 'Carbon monoxide from vehicles and burning of waste',
    NH3: 'Ammonia from agricultural burning and sewage',
    NO2: 'Nitrogen dioxide from diesel vehicles and power plants',
    NOx: 'Nitrogen oxides from vehicle exhausts and industries',
    SO2: 'Sulphur dioxide from coal burning power plants',
    Benzene: 'Benzene from petrol vehicles and fuel evaporation',
    Ozone: 'Ground level ozone formed from sunlight reacting with other pollutants',
    season_enc:
      'Seasonal effects such as winter temperature inversions',
    month: 'Monthly variation in pollution patterns',
  };
  return explanations[pollutant] || pollutant;
}

export function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

export function formatNumber(num: number, decimals: number = 1): string {
  return num.toFixed(decimals);
}
