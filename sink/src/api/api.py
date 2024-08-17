# this is the general script to use for accessing the api
import argparse
import requests
import settings

print(settings.APIRoutes.BASE_URL)
print(settings.APIConfigs.SECRET_KEY)

#TODO: implement api functions