import requests, json, argparse,sys, logging, statistics
from datetime import date
from decimal import Decimal


#Base REST endpoints
base_url = "https://api.gemini.com/v1"
base_urlv2 = "https://api.gemini.com/v2"


#Setup program description and arguments and basic logging functionality 
parser = argparse.ArgumentParser(prog='GeminiAlert', usage='%(prog)s [options]', description="A simple alerting program fed from the the public Gemini API")
logging.basicConfig(level=20, format='%(asctime)s,%(msecs)03d - %(levelname)s - %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
logging.info("Running " + sys.argv[0])

#Percentage class for deviation change for arguments
class Percent(object):
    def __new__(self,  percent_string):
        if not percent_string.endswith('%'):
            raise ValueError('Need percent got {}'.format(percent_string))
        value = float(percent_string[:-1]) * 0.01
        return value

#Arguments available to user
parser.add_argument('-c', '--currency', type=str.lower, help="the currency trading pair or all",required=True)
parser.add_argument('-t', '--type', type=str.lower, help="the type of check to run", choices=['pricedev','pricechange','voldev','all'])
parser.add_argument('-d', '--deviation', type=Percent, help="Percentage threshold for deviation change, values should be entered with a percentage sign. Default is 5 percent", default="5%")
args = parser.parse_args()

#Symbol functions - common
def getSymPrice():
  response = requests.get(base_url + "/pubticker/"+args.currency)
  currency = response.json()
  price_in_decimal = Decimal(currency["last"].replace(',','.'))
  return price_in_decimal

def getAllSymPriceDict():
  response = requests.get(base_url + "/symbols")
  symbols = response.json()
  priceArr = []
  for sym in symbols:  
    response = requests.get(base_url + "/pubticker/"+sym)
    currency = response.json()
    priceArr.append(currency["last"])
  [float(i) for i in priceArr]
  zip_iterator = zip(symbols,priceArr)
  dictionary = dict(zip_iterator)
  return dictionary

# Functions for Deviation
def priceDevMean():
  response = requests.get(base_urlv2 + "/ticker/"+args.currency)
  currencyv2 = response.json()
  devSet = currencyv2["changes"]
  decConv = [Decimal(x.strip(' ')) for x in devSet]
  mean = statistics.mean(decConv)
  logging.info("Mean Deviation of sample is %s" % (mean))
  return mean 

def priceDevStdev():
  response = requests.get(base_urlv2 + "/ticker/"+args.currency)
  currencyv2 = response.json()
  devSet = currencyv2["changes"]
  decConv = [Decimal(x.strip(' ')) for x in devSet]
  stdev = statistics.stdev(decConv)
  logging.info("Standard Deviation of sample is %s" % (stdev))
  return stdev

def priceDiffAvg():
  symPrice = getSymPrice()
  mean = priceDevMean()
  diff = abs(mean - symPrice)
  logging.info("Price difference is %s " %(diff))
  return diff

def deviationAlert():
  avg = priceDiffAvg()
  stdev = priceDevStdev()
  if avg <= stdev:
    logging.info("Price is within standard deviation - all good!")
  else:
    logging.error("Price is outside of the standard deviation!")
### End Deviation functions 

# Functions for pricechange
def getOpenPrice():
  response = requests.get(base_urlv2 + "/ticker/"+args.currency)
  currencyv2 = response.json()
  openPrice = currencyv2["open"]
  dec = float(openPrice)
  return dec

def priceChangeAlert():
  currentPrice = getSymPrice()
  openPrice = getOpenPrice()
  logging.info("Open price is %s " %(openPrice))
  percentChangeOpen = openPrice * args.deviation
  logging.info("Percentage change specified is %s " %(args.deviation))
  lowerBound = openPrice - percentChangeOpen
  upperBound = openPrice + percentChangeOpen
  if currentPrice <= upperBound and currentPrice >= lowerBound:
    logging.info("Current price is within the percentage change of the open price - all good!")
  else:
    logging.error("Current price is not withing the percentage change specified of the open price - throwing alert")
### End functions for pricechange

# Voldev functions
def getSymTotalVolume():
  response = requests.get(base_url + "/pubticker/"+args.currency)
  currency = response.json()
  symVol = currency["volume"]
  symTotal = list(symVol.values())[0]
  dec = float(symTotal)
  return dec

def volumeDeviationAlert():
  #unsure how this can be measured for the req of "current" i am using the 1 hour volume. total volume / 24
  totalVol = getSymTotalVolume()
  logging.info("Total volume is: %s"  %(totalVol))
  currentVol = totalVol /24 
  logging.info("Current volume (1 hour) is: %s"  %(currentVol))
  percentVol = totalVol * args.deviation
  logging.info("deviation is set to: %s" %(args.deviation))
  logging.info("Percentage of deviation is: %s"  %(percentVol))
  if currentVol >= percentVol:
    logging.error("current volume: %s"  %(currentVol) + " is greater than %s" %(args.deviation) + " percentage of volume total %s" %(totalVol))
  else: 
    logging.info("Volume is within percentage deviation - no issues!")
### End functions for voldev

#Arg Parse output
for arg in vars(args):
  logging.info("Parsing arg: " + arg )

#Pull Symbols from /symbols endpoint
try:
  response = requests.get(base_url + "/symbols")
  symbols = response.json()
  logging.info("Getting symbol API data") 
except requests.ConnectionError as e:
  logging.error("The request failed please check your connection and error below:")
  print(str(e))
except requests.Timeout as e:
  logging.error("The request timedout please check your connection and error below:")
  print(str(e)) 

#Main logic block for Arg handling
#currency pair handling
if args.currency in symbols: 
  logging.info("got " + args.currency + " pair from symbol data")
  logging.info(args.currency + " current price is %s "  %(getSymPrice()))
elif args.currency == "all":
  d = getAllSymPriceDict()
  for key,value in d.items():
    logging.info("got symbol: " +key + " current price is:  " +value)
elif args.currency not in symbols:
  logging.error("invalid currency pair - did you enter a bad value?...exiting")     

# type checks handling
if args.currency == "all" and args.type == "all":
  # Here i can out of time and would need a bit of a refactor to have all checks for every currency handling the "all" argument a bit better in my methods. 
  print("All / All usecase")
elif args.type == "pricedev":
  deviationAlert()
elif args.type == "pricechange":
  priceChangeAlert()
elif args.type =="voldev":
  volumeDeviationAlert()
#single currency all checks
elif args.type == "all":
  deviationAlert()
  priceChangeAlert()
  volumeDeviationAlert()