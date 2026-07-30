import gzip
import urllib.request
CONCEPTNET_URL = "https://s3.amazonaws.com/conceptnet/downloads/2019/edges/conceptnet-assertions-5.7.0.csv.gz"

req = urllib.request.Request(CONCEPTNET_URL, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as response:
    with gzip.GzipFile(fileobj=response) as gz:
        for i, line in enumerate(gz):
            print(repr(line))
            if i >= 5:
                break
