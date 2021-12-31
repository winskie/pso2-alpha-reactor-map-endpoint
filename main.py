#! /usr/bin/env python
# coding=utf8

import os
import requests
import configparser
from datetime import datetime, timedelta

config = configparser.ConfigParser(interpolation=None)
config.read("config.ini")


def get_tweets(since_id=None):
  endpoint_url = "https://api.twitter.com/2/users/" + config["Twitter"]["user_id"] + "/tweets"
  start_time = datetime.today() - timedelta(int(config["Settings"]["max_historical_days"]))
  headers = {
      "Authorization": "Bearer " + config["Twitter"]["bearer_token"]
    }
  params = {
      "exclude": "retweets,replies",
      "max_results": 100,
      "expansions": "attachments.media_keys,author_id",
      "tweet.fields": "created_at",
      "media.fields": "url,type,height,width",
      "user.fields": "username,profile_image_url",
      "start_time": start_time.strftime("%Y-%m-%dT00:00:00Z")
    }

  # We have a known last posted ID:
  if since_id:
    params["since_id"] = since_id
  
  response = requests.get(endpoint_url, headers=headers, params=params)

  if response.status_code == 200:
    return response.json()
  else:
    raise Exception("Unexpected response from server: {status_code}".format(status_code=response.status_code))


def post_maps(map_tweets=None):

  if map_tweets:
    posted_ids = []
    # Reverse the order of the tweets from earliest to latest:
    for mt in reversed(map_tweets):

      # Get extra information and remove from embed data:
      username = mt["username"]
      del mt["username"]

      data = {
        #"avatar_url": "https://cdn.discordapp.com/avatars/860982741806088232/2eefbe56d88fa45c7234f7f7a75359f5.png",
        "content": None,
        "embeds": [mt]
      }

      if not len(username):
        username = config["Settings"]["display_username"].strip()

      data["username"] = username

      # Post map:
      webhook_url = config["Discord"]["webhook_url"] + '?wait=1'
      response = requests.post(webhook_url, json=data)
      
      if response.status_code == 200:
        data = response.json()
        posted_ids.append(data["id"])

    # Delete previous posted tweets:
    delete_url = config["Discord"]["webhook_url"] + "/messages/"
    previous_posted_ids = config["Settings"]["last_posted_id"].split(",")
    if len(previous_posted_ids):
      for id in previous_posted_ids:
        requests.delete(delete_url + id)

    # Write settings:
    config["Settings"]["last_posted_id"] = ",".join(posted_ids)
    with open("config.ini", "w") as configfile:
      config.write(configfile)


def main():
  # Get alpha reactor map tweets starting from last known posted tweet ID:
  map_tweets = []
  response = get_tweets(config["Settings"]["last_checked_id"])
  last_checked_id = config["Settings"]["last_checked_id"]

  if "data" in response:

    # Create mapping for media:
    media_map = {}
    if "includes" in response and "media" in response["includes"]:
      for m in response["includes"]["media"]:
        media_map[m["media_key"]] = m

    # Create mapping for user:
    user_map = {}
    if "includes" in response and "users" in response["includes"]:
      for u in response["includes"]["users"]:
        user_map[u["id"]] = u

    # Substrings to look for:
    substring_list = [
      "#AlphaReactors #アルファリアクター #PSO2NGS",
      "#PSO2NGS #PhotonScales #フォトンスケイル"
    ]

    for d in response["data"]:
      # Alpha Reactor Location Map:
      if d["text"].find("#AlphaReactors #アルファリアクター #PSO2NGS") >= 0:
        # We have a possible alpha reactor map tweet:
        created_at = datetime.strptime(d['created_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
        embed_data = {
          "id": d["id"],
          "title": None,
          "description": d["text"],
          "color": 16294421,
          "author": None,
          "footer": {
            "text": "Tweet created last " + created_at.strftime('%Y-%m-%d %H:%M') + " UTC",
            #"icon_url": "https://images-ext-2.discordapp.net/external/7MOaFXHz8bM42aaNcsmATUh2u0CBwwTHnHBfBs1z7tQ/https/cdn1.iconfinder.com/data/icons/iconza-circle-social/64/697029-twitter-512.png"
          },
          "image": None,

          # Extra information to be passed to post function:
          "username": "Alpha Reactor Locator"
        }

        # Attach author information:
        if d["author_id"] in user_map:
          user = user_map[d["author_id"]]
          embed_data["title"] = user["name"]
          embed_data["url"] = "https://twitter.com/{username}/status/{tweet_id}".format(username=user["username"], tweet_id=d["id"])
          embed_data["author"] = {
            "name": user["username"] + " - Alpha Reactor Location Map",
            "icon_url": user["profile_image_url"]
          }

        # Attach image:
        if "attachments" in d:
          for m in d["attachments"]["media_keys"]:
            if m in media_map:
              embed_data["image"] = {
                "url": media_map[m]["url"]
              }
              break
        
        map_tweets.append(embed_data)

      # Photon Scale Location Map:
      elif d["text"].find("#PSO2NGS #PhotonScales #フォトンスケイル") >= 0:
        # We have a possible alpha reactor map tweet:
        created_at = datetime.strptime(d['created_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
        embed_data = {
          "id": d["id"],
          "title": None,
          "description": d["text"],
          "color": 1299449,
          "author": None,
          "footer": {
            "text": "Tweet created last " + created_at.strftime('%Y-%m-%d %H:%M') + " UTC",
            #"icon_url": "https://images-ext-2.discordapp.net/external/7MOaFXHz8bM42aaNcsmATUh2u0CBwwTHnHBfBs1z7tQ/https/cdn1.iconfinder.com/data/icons/iconza-circle-social/64/697029-twitter-512.png"
          },
          "image": None,

          # Extra information to be passed to post function:
          "username": "Photo Scale Locator"
        }

        # Attach author information:
        if d["author_id"] in user_map:
          user = user_map[d["author_id"]]
          embed_data["title"] = user["name"]
          embed_data["url"] = "https://twitter.com/{username}/status/{tweet_id}".format(username=user["username"], tweet_id=d["id"])
          embed_data["author"] = {
            "name": user["username"] + " - Photon Scale Location Map",
            "icon_url": user["profile_image_url"]
          }

        # Attach image:
        if "attachments" in d:
          for m in d["attachments"]["media_keys"]:
            if m in media_map:
              embed_data["image"] = {
                "url": media_map[m]["url"]
              }
              break
        
        map_tweets.append(embed_data)

      if last_checked_id < d["id"]:
        last_checked_id = d["id"]

    # Write last checked tweet settings:
    config["Settings"]["last_checked_id"] = last_checked_id
    with open("config.ini", "w") as configfile:
      config.write(configfile)

    if len(map_tweets):
      # We have possible tweets of the map, let's post them:
      post_maps(map_tweets)
    else:
      print("No possible alpha reactor map found. Exiting...")

    return
  
  else:
    print("No tweets to process. Exiting...")
    return


if __name__ == "__main__":
  main()