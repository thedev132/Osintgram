import datetime
import json
import sys
import urllib
import os
import codecs
from pathlib import Path
import subprocess


import requests
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

from geopy.geocoders import Nominatim
from instagrapi import Client as AppClient
from instagrapi.exceptions import ClientError
import instaloader as Loader
from prettytable import PrettyTable

from src import printcolors as pc
from src import config
client = AppClient()
loader = Loader.Instaloader()



class Osintgram:
    api = None
    api2 = None
    geolocator = Nominatim(user_agent="http")
    user_id = None
    target_id = None
    is_private = True
    following = False
    target = ""
    writeFile = False
    jsonDump = False
    cli_mode = False
    output_dir = "output"


    def __init__(self, target, is_cli):
        u = config.getUsername()
        p = config.getPassword()
        self.cli_mode = is_cli
        if not is_cli:
          print("\nAttempt to login...")
        self.login(u, p)
        self.setTarget(target)

    def setTarget(self, target):
        self.target = target
        user = self.get_user(target)
        self.target_id = user['id']
        self.is_private = user['is_private']
        self.following = self.check_following(config.getUsername())
        self.__printTargetBanner__()


    def __get_comments__(self, media_id):
        comments = []

        result = self.api.media_comments(str(media_id))
        comments.extend(result.get('comments', []))

        next_max_id = result.get('next_max_id')
        while next_max_id:
            results = self.api.media_comments(str(media_id), max_id=next_max_id)
            comments.extend(results.get('comments', []))
            next_max_id = results.get('next_max_id')

        return comments

    def __printTargetBanner__(self):
        pc.printout("\nLogged as ", pc.GREEN)
        pc.printout(config.getUsername(), pc.CYAN)
        pc.printout(". Target: ", pc.GREEN)
        pc.printout(str(self.target), pc.CYAN)
        pc.printout(" [" + str(self.target_id) + "]")
        if self.is_private:
            pc.printout(" [PRIVATE PROFILE]", pc.BLUE)
        if self.following:
            pc.printout(" [FOLLOWING]", pc.GREEN)
        else:
            pc.printout(" [NOT FOLLOWING]", pc.RED)

        print('\n')

    def change_target(self):
        pc.printout("Insert new target username: ", pc.YELLOW)
        line = input()
        self.setTarget(line)
        return

    # def get_addrs(self):
    #     if self.check_private_profile():
    #         return

    #     pc.printout("Searching for target localizations...\n")

    #     data = self.__get_feed__()

    #     locations = {}

    #     for post in data:
    #         if 'location' in post and post['location'] is not None:
    #             if 'lat' in post['location'] and 'lng' in post['location']:
    #                 lat = post['location']['lat']
    #                 lng = post['location']['lng']
    #                 locations[str(lat) + ', ' + str(lng)] = post.get('taken_at')

    #     address = {}
    #     for k, v in locations.items():
    #         details = self.geolocator.reverse(k)
    #         unix_timestamp = datetime.datetime.fromtimestamp(v)
    #         address[details.address] = unix_timestamp.strftime('%Y-%m-%d %H:%M:%S')

    #     sort_addresses = sorted(address.items(), key=lambda p: p[1], reverse=True)

    #     if len(sort_addresses) > 0:
    #         t = PrettyTable()

    #         t.field_names = ['Post', 'Address', 'time']
    #         t.align["Post"] = "l"
    #         t.align["Address"] = "l"
    #         t.align["Time"] = "l"
    #         pc.printout("\nWoohoo! We found " + str(len(sort_addresses)) + " addresses\n", pc.GREEN)

    #         i = 1

    #         json_data = {}
    #         addrs_list = []

    #         for address, time in sort_addresses:
    #             t.add_row([str(i), address, time])

    #             if self.jsonDump:
    #                 addr = {
    #                     'address': address,
    #                     'time': time
    #                 }
    #                 addrs_list.append(addr)

    #             i = i + 1

    #         if self.writeFile:
    #             file_name = self.output_dir + "/" + self.target + "_addrs.txt"
    #             file = open(file_name, "w")
    #             file.write(str(t))
    #             file.close()

    #         if self.jsonDump:
    #             json_data['address'] = addrs_list
    #             json_file_name = self.output_dir + "/" + self.target + "_addrs.json"
    #             with open(json_file_name, 'w') as f:
    #                 json.dump(json_data, f)

    #         print(t)
    #     else:
    #         pc.printout("Sorry! No results found :-(\n", pc.RED)

    # def get_captions(self):
    #     if self.check_private_profile():
    #         return

    #     pc.printout("Searching for target captions...\n")

    #     captions = []

    #     data = self.__get_feed__()
    #     counter = 0

    #     try:
    #         for item in data:
    #             if "caption" in item:
    #                 if item["caption"] is not None:
    #                     text = item["caption"]["text"]
    #                     captions.append(text)
    #                     counter = counter + 1
    #                     sys.stdout.write("\rFound %i" % counter)
    #                     sys.stdout.flush()

    #     except AttributeError:
    #         pass

    #     except KeyError:
    #         pass

    #     json_data = {}

    #     if counter > 0:
    #         pc.printout("\nWoohoo! We found " + str(counter) + " captions\n", pc.GREEN)

    #         file = None

    #         if self.writeFile:
    #             file_name = self.output_dir + "/" + self.target + "_captions.txt"
    #             file = open(file_name, "w")

    #         for s in captions:
    #             print(s + "\n")

    #             if self.writeFile:
    #                 file.write(s + "\n")

    #         if self.jsonDump:
    #             json_data['captions'] = captions
    #             json_file_name = self.output_dir + "/" + self.target + "_followings.json"
    #             with open(json_file_name, 'w') as f:
    #                 json.dump(json_data, f)

    #         if file is not None:
    #             file.close()

    #     else:
    #         pc.printout("Sorry! No results found :-(\n", pc.RED)

    #     return

    def get_total_comments(self):
        if self.check_private_profile():
            return

        pc.printout("Searching for target total comments...\n")

        comments_counter = 0
        posts = 0

        data = self.__get_feed__()

        for post in data:
            comments_counter += post['comment_count']
            posts += 1

        if self.writeFile:
            file_name = self.output_dir + "/" + self.target + "_comments.txt"
            file = open(file_name, "w")
            file.write(str(comments_counter) + " comments in " + str(posts) + " posts\n")
            file.close()

        if self.jsonDump:
            json_data = {
                'comment_counter': comments_counter,
                'posts': posts
            }
            json_file_name = self.output_dir + "/" + self.target + "_comments.json"
            with open(json_file_name, 'w') as f:
                json.dump(json_data, f)

        pc.printout(str(comments_counter), pc.MAGENTA)
        pc.printout(" comments in " + str(posts) + " posts\n")

    def get_comment_data(self):
        if self.check_private_profile():
            return

        pc.printout("Retrieving all comments, this may take a moment...\n")
        data = self.__get_feed__()
        
        _comments = []
        t = PrettyTable(['POST ID', 'ID', 'Username', 'Comment'])
        t.align["POST ID"] = "l"
        t.align["ID"] = "l"
        t.align["Username"] = "l"
        t.align["Comment"] = "l"

        for post in data:
            post_id = post.get('id')
            comments = self.api.media_n_comments(post_id)
            for comment in comments:
                t.add_row([post_id, comment.get('user_id'), comment.get('user').get('username'), comment.get('text')])
                comment = {
                        "post_id": post_id,
                        "user_id":comment.get('user_id'), 
                        "username": comment.get('user').get('username'),
                        "comment": comment.get('text')
                    }
                _comments.append(comment)
        
        print(t)
        if self.writeFile:
            file_name = self.output_dir + "/" + self.target + "_comment_data.txt"
            with open(file_name, 'w') as f:
                f.write(str(t))
                f.close()
        
        if self.jsonDump:
            file_name_json = self.output_dir + "/" + self.target + "_comment_data.json"
            with open(file_name_json, 'w') as f:
                f.write("{ \"Comments\":[ \n")
                f.write('\n'.join(json.dumps(comment) for comment in _comments) + ',\n')
                f.write("]} ")


    def get_followers(self):
        if self.check_private_profile():
            return

        pc.printout("Searching for target followers (this may take a while) ...\n")

        _followers = []
        followers = []


        data = client.user_followers(str(self.target_id))
        _followers.extend(data.values())

        print("\n")
            
        for user in _followers:
            userDict = user.dict()
            u = {
                'id': userDict['pk'],
                'username': userDict['username'],
                'full_name': userDict['full_name']
            }
            followers.append(u)

        t = PrettyTable(['ID', 'Username', 'Full Name'])
        t.align["ID"] = "l"
        t.align["Username"] = "l"
        t.align["Full Name"] = "l"

        json_data = {}
        followings_list = []

        for node in followers:
            t.add_row([str(node['id']), node['username'], node['full_name']])

            if self.jsonDump:
                follow = {
                    'id': node['id'],
                    'username': node['username'],
                    'full_name': node['full_name']
                }
                followings_list.append(follow)

        if self.writeFile:
            file_name = self.output_dir + "/" + self.target + "_followers.txt"
            file = open(file_name, "w")
            file.write(str(t))
            file.close()

        if self.jsonDump:
            json_data['followers'] = followers
            json_file_name = self.output_dir + "/" + self.target + "_followers.json"
            with open(json_file_name, 'w') as f:
                json.dump(json_data, f)

        print(t)

    def get_followings(self):
        if self.check_private_profile():
            return

        pc.printout("Searching for target followings...\n")

        _followings = []
        followings = []

        data = client.user_following(str(self.target_id), 0)
        _followings.extend(data.values())

        print("\n")

        for user in _followings:
            userDict = user.dict()
            u = {
                'id': userDict['pk'],
                'username': userDict['username'],
                'full_name': userDict['full_name']
            }
            followings.append(u)

        t = PrettyTable(['ID', 'Username', 'Full Name'])
        t.align["ID"] = "l"
        t.align["Username"] = "l"
        t.align["Full Name"] = "l"

        json_data = {}
        followings_list = []

        for node in followings:
            t.add_row([str(node['id']), node['username'], node['full_name']])

            if self.jsonDump:
                follow = {
                    'id': node['id'],
                    'username': node['username'],
                    'full_name': node['full_name']
                }
                followings_list.append(follow)

        if self.writeFile:
            file_name = self.output_dir + "/" + self.target + "_followings.txt"
            file = open(file_name, "w")
            file.write(str(t))
            file.close()

        if self.jsonDump:
            json_data['followings'] = followings_list
            json_file_name = self.output_dir + "/" + self.target + "_followings.json"
            with open(json_file_name, 'w') as f:
                json.dump(json_data, f)

        print(t)

    def get_hashtags(self):
        if self.check_private_profile():
            return

        pc.printout("Searching for target hashtags...\n")

        hashtags = []
        hashtagsDict = {}
        counter = 0

        medias = client.user_medias(str(self.target_id))
        for post in medias:
            caption = client.media_info(post.pk).dict()['caption_text']
            hashtags = [word for word in caption.split() if word.startswith('#')]
            for hashtag in hashtags:
                if hashtag in hashtagsDict:
                    hashtagsDict[hashtag] += 1
                else:
                    hashtagsDict[hashtag] = 1
                counter += 1

        t = PrettyTable(['Hashtag', 'Count'])
        t.align["Hastag"] = "l"
        t.align["Count"] = "l"

        for node in hashtagsDict:
            t.add_row([str(node), str(hashtagsDict[node])])

        if len(hashtags) > 0:  
            pc.printout("We found " + str(counter) + " hashtags\n", pc.GREEN)

            print(t)

            # file = None
            # json_data = {}
            # hashtags_list = []

            # if self.writeFile:
            #     file_name = self.output_dir + "/" + self.target + "_hashtags.txt"
            #     file = open(file_name, "w")

            # if file is not None:
            #     file.close()

            # if self.jsonDump:
            #     json_data['hashtags'] = hashtags_list
            #     json_file_name = self.output_dir + "/" + self.target + "_hashtags.json"
            #     with open(json_file_name, 'w') as f:
            #         json.dump(json_data, f)
        else:
            pc.printout("Sorry! No results found :-(\n", pc.RED)

    def get_user_info(self):
        try:
            content = client.user_info_by_username(self.target).dict()
            
            pc.printout("[ID] ", pc.GREEN)
            pc.printout(str(content['pk']) + '\n')
            pc.printout("[FULL NAME] ", pc.RED)
            pc.printout(str(content['full_name']) + '\n')
            pc.printout("[BIOGRAPHY] ", pc.CYAN)
            pc.printout(str(content['biography']) + '\n')
            pc.printout("[FOLLOWED] ", pc.BLUE)
            pc.printout(str(content['follower_count']) + '\n')
            pc.printout("[FOLLOW] ", pc.GREEN)
            pc.printout(str(content['following_count']) + '\n')
            pc.printout("[BUSINESS ACCOUNT] ", pc.RED)
            pc.printout(str(content['is_business']) + '\n')
            pc.printout("[VERIFIED ACCOUNT] ", pc.CYAN)
            pc.printout(str(content['is_verified']) + '\n')
            if 'public_email' in content and content['public_email']:
                pc.printout("[EMAIL] ", pc.BLUE)
                pc.printout(str(content['public_email']) + '\n')
            pc.printout("[HD PROFILE PIC] ", pc.GREEN)
            pc.printout(str(content['profile_pic_url']) + '\n')
            if 'fb_page_call_to_action_id' in content and content['fb_page_call_to_action_id']: 
                pc.printout("[FB PAGE] ", pc.RED)
                pc.printout(str(content['connected_fb_page']) + '\n')
            if 'whatsapp_number' in content and content['whatsapp_number']:
                pc.printout("[WHATSAPP NUMBER] ", pc.GREEN)
                pc.printout(str(content['whatsapp_number']) + '\n')
            if 'city_name' in content and content['city_name']:
                pc.printout("[CITY] ", pc.YELLOW)
                pc.printout(str(content['city_name']) + '\n')
            if 'address_street' in content and content['address_street']:
                pc.printout("[ADDRESS STREET] ", pc.RED)
                pc.printout(str(content['address_street']) + '\n')
            if 'contact_phone_number' in content and content['contact_phone_number']:
                pc.printout("[CONTACT PHONE NUMBER] ", pc.CYAN)
                pc.printout(str(content['contact_phone_number']) + '\n')
            if self.jsonDump:
                user = {
                    'id': content['pk'],
                    'full_name': content['full_name'],
                    'biography': content['biography'],
                    'edge_followed_by': content['follower_count'],
                    'edge_follow': content['following_count'],
                    'is_business_account': content['is_business'],
                    'is_verified': content['is_verified'],
                    'profile_pic_url_hd': content['profile_pic_url']
                }
                json_file_name = self.output_dir + "/" + self.target + "_info.json"
                with open(json_file_name, 'w') as f:
                    json.dump(user, f)

        except ClientError as e:
            print(e)
            pc.printout("Oops... " + str(self.target) + " non exist, please enter a valid username.", pc.RED)
            pc.printout("\n")
            exit(2)

    def get_total_likes(self):
        if self.check_private_profile():
            return

        pc.printout("Searching for target total likes...\n")

        like_counter = 0
        posts_counter = 0

        medias = client.user_medias(str(self.target_id))

        for post in medias:
            likes = client.media_info(post.pk).dict()['like_count']
            like_counter += likes
            posts_counter += 1

        if self.writeFile:
            file_name = self.output_dir + "/" + self.target + "_likes.txt"
            file = open(file_name, "w")
            file.write(str(like_counter) + " likes in " + str(like_counter) + " posts\n")
            file.close()

        if self.jsonDump:
            json_data = {
                'like_counter': like_counter,
                'posts': like_counter
            }
            json_file_name = self.output_dir + "/" + self.target + "_likes.json"
            with open(json_file_name, 'w') as f:
                json.dump(json_data, f)

        pc.printout(str(like_counter), pc.MAGENTA)
        if like_counter == 1:
            pc.printout(" like in " + str(posts_counter) + " post\n")
        else:
            pc.printout(" likes in " + str(posts_counter) + " posts\n")

    def get_media_type(self):
        if self.check_private_profile():
            return

        pc.printout("Searching for target captions...\n")

        counter = 0
        photo_counter = 0
        video_counter = 0

        data = self.__get_feed__()

        for post in data:
            if "media_type" in post:
                if post["media_type"] == 1:
                    photo_counter = photo_counter + 1
                elif post["media_type"] == 2:
                    video_counter = video_counter + 1
                counter = counter + 1
                sys.stdout.write("\rChecked %i" % counter)
                sys.stdout.flush()

        sys.stdout.write(" posts")
        sys.stdout.flush()

        if counter > 0:

            if self.writeFile:
                file_name = self.output_dir + "/" + self.target + "_mediatype.txt"
                file = open(file_name, "w")
                file.write(str(photo_counter) + " photos and " + str(video_counter) + " video posted by target\n")
                file.close()

            pc.printout("\nWoohoo! We found " + str(photo_counter) + " photos and " + str(video_counter) +
                        " video posted by target\n", pc.GREEN)

            if self.jsonDump:
                json_data = {
                    "photos": photo_counter,
                    "videos": video_counter
                }
                json_file_name = self.output_dir + "/" + self.target + "_mediatype.json"
                with open(json_file_name, 'w') as f:
                    json.dump(json_data, f)

        else:
            pc.printout("Sorry! No results found :-(\n", pc.RED)

    def get_people_who_commented(self):
        if self.check_private_profile():
            return

        pc.printout("Searching for users who commented...\n")

        data = self.__get_feed__()
        users = []

        for post in data:
            comments = self.__get_comments__(post['id'])
            for comment in comments:
                if not any(u['id'] == comment['user']['pk'] for u in users):
                    user = {
                        'id': comment['user']['pk'],
                        'username': comment['user']['username'],
                        'full_name': comment['user']['full_name'],
                        'counter': 1
                    }
                    users.append(user)
                else:
                    for user in users:
                        if user['id'] == comment['user']['pk']:
                            user['counter'] += 1
                            break

        if len(users) > 0:
            ssort = sorted(users, key=lambda value: value['counter'], reverse=True)

            json_data = {}

            t = PrettyTable()

            t.field_names = ['Comments', 'ID', 'Username', 'Full Name']
            t.align["Comments"] = "l"
            t.align["ID"] = "l"
            t.align["Username"] = "l"
            t.align["Full Name"] = "l"

            for u in ssort:
                t.add_row([str(u['counter']), u['id'], u['username'], u['full_name']])

            print(t)

            if self.writeFile:
                file_name = self.output_dir + "/" + self.target + "_users_who_commented.txt"
                file = open(file_name, "w")
                file.write(str(t))
                file.close()

            if self.jsonDump:
                json_data['users_who_commented'] = ssort
                json_file_name = self.output_dir + "/" + self.target + "_users_who_commented.json"
                with open(json_file_name, 'w') as f:
                    json.dump(json_data, f)
        else:
            pc.printout("Sorry! No results found :-(\n", pc.RED)

    def get_people_who_tagged(self):
        if self.check_private_profile():
            return

        pc.printout("Searching for users who tagged target...\n")

        posts = []

        result = self.api.usertag_feed(self.target_id)
        posts.extend(result.get('items', []))

        next_max_id = result.get('next_max_id')
        while next_max_id:
            results = self.api.user_feed(str(self.target_id), max_id=next_max_id)
            posts.extend(results.get('items', []))
            next_max_id = results.get('next_max_id')

        if len(posts) > 0:
            pc.printout("\nWoohoo! We found " + str(len(posts)) + " photos\n", pc.GREEN)

            users = []

            for post in posts:
                if not any(u['id'] == post['user']['pk'] for u in users):
                    user = {
                        'id': post['user']['pk'],
                        'username': post['user']['username'],
                        'full_name': post['user']['full_name'],
                        'counter': 1
                    }
                    users.append(user)
                else:
                    for user in users:
                        if user['id'] == post['user']['pk']:
                            user['counter'] += 1
                            break

            ssort = sorted(users, key=lambda value: value['counter'], reverse=True)

            json_data = {}

            t = PrettyTable()

            t.field_names = ['Photos', 'ID', 'Username', 'Full Name']
            t.align["Photos"] = "l"
            t.align["ID"] = "l"
            t.align["Username"] = "l"
            t.align["Full Name"] = "l"

            for u in ssort:
                t.add_row([str(u['counter']), u['id'], u['username'], u['full_name']])

            print(t)

            if self.writeFile:
                file_name = self.output_dir + "/" + self.target + "_users_who_tagged.txt"
                file = open(file_name, "w")
                file.write(str(t))
                file.close()

            if self.jsonDump:
                json_data['users_who_tagged'] = ssort
                json_file_name = self.output_dir + "/" + self.target + "_users_who_tagged.json"
                with open(json_file_name, 'w') as f:
                    json.dump(json_data, f)
        else:
            pc.printout("Sorry! No results found :-(\n", pc.RED)

    def get_photo_description(self):
        if self.check_private_profile():
            return

        content = requests.get("https://www.instagram.com/" + str(self.target) + "/?__a=1")
        data = content.json()

        dd = data['graphql']['user']['edge_owner_to_timeline_media']['edges']

        if len(dd) > 0:
            pc.printout("\nWoohoo! We found " + str(len(dd)) + " descriptions\n", pc.GREEN)

            count = 1

            t = PrettyTable(['Photo', 'Description'])
            t.align["Photo"] = "l"
            t.align["Description"] = "l"

            json_data = {}
            descriptions_list = []

            for i in dd:
                node = i.get('node')
                descr = node.get('accessibility_caption')
                t.add_row([str(count), descr])

                if self.jsonDump:
                    description = {
                        'description': descr
                    }
                    descriptions_list.append(description)

                count += 1

            if self.writeFile:
                file_name = self.output_dir + "/" + self.target + "_photodes.txt"
                file = open(file_name, "w")
                file.write(str(t))
                file.close()

            if self.jsonDump:
                json_data['descriptions'] = descriptions_list
                json_file_name = self.output_dir + "/" + self.target + "_descriptions.json"
                with open(json_file_name, 'w') as f:
                    json.dump(json_data, f)

            print(t)
        else:
            pc.printout("Sorry! No results found :-(\n", pc.RED)

    def get_user_photo(self):
        if self.check_private_profile():
            return

        pc.printout("Searching for target photos...\n")
        profile = Loader.Profile.from_username(loader.context, self.target)
        posts = profile.get_posts()
        try:
            for post in posts:
                loader.download_post(post, self.target)
        except KeyboardInterrupt:
            posts.freeze()

        
    def get_user_propic(self):
        userInfo = client.user_info_by_username(self.target).dict()
        url = userInfo['profile_pic_url']
        response = requests.get(url)
        #path is the root directory/username of the target folder 
        path = self.target + "/"
        if not os.path.exists(path):
            os.makedirs(path)
        open(path + 'propic.jpg', 'wb').write(response.content)
        print("🎉 Profile picture saved in \"" + path + "propic.jpg\" 😄")
    def get_user_stories(self):
        if self.check_private_profile():
            return

        pc.printout("Searching for target stories...\n")
        profile = Loader.Profile.from_username(loader.context, self.target)
        loader.download_stories([profile])

    def get_user_highlights(self):
        if self.check_private_profile():
            return

        pc.printout("Searching for target highlights...\n")
        profile = Loader.Profile.from_username(loader.context, self.target)
        loader.download_highlights(profile)


    def get_people_tagged_by_user(self):
        pc.printout("Searching for users tagged by target...\n")

        ids = []
        username = []
        full_name = []
        postList = []
        counter = 1

        profile = Loader.Profile.from_username(loader.context, self.target)
        posts = profile.get_posts()
        try:
            for post in posts:
                taggedUsers = post.tagged_users
                for users in taggedUsers:
                    profile = Loader.Profile.from_username(loader.context, users)
                    ids.append(profile.userid)
                    username.append(users)
                    full_name.append(profile.full_name)
                    postList.append(post.mediaid)
                    # counter = counter + 1
                    # sys.stdout.write("\rCatched %i" % counter)
                    # sys.stdout.flush()
        except KeyboardInterrupt:
            posts.freeze()

        if len(ids) > 0:
            t = PrettyTable()

            t.field_names = ['Posts', 'Full Name', 'Username', 'ID']
            t.align["Posts"] = "l"
            t.align["Full Name"] = "l"
            t.align["Username"] = "l"
            t.align["ID"] = "l"

            pc.printout("\nWoohoo! We found " + str(len(ids)) + " (" + str(counter) + ") users\n", pc.GREEN)

            json_data = {}
            tagged_list = []

            for i in range(len(ids)):
                t.add_row([postList[i], full_name[i], username[i], str(ids[i])])

                if self.jsonDump:
                    tag = {
                        'post': post[i],
                        'full_name': full_name[i],
                        'username': username[i],
                        'id': ids[i]
                    }
                    tagged_list.append(tag)

            if self.writeFile:
                file_name = self.output_dir + "/" + self.target + "_tagged.txt"
                file = open(file_name, "w")
                file.write(str(t))
                file.close()

            if self.jsonDump:
                json_data['tagged'] = tagged_list
                json_file_name = self.output_dir + "/" + self.target + "_tagged.json"
                with open(json_file_name, 'w') as f:
                    json.dump(json_data, f)

            print(t)
        else:
            pc.printout("Sorry! No results found :-(\n", pc.RED)

    def get_user(self, username):
        try:
            user = dict()
            content = client.user_info_by_username(username).dict()
            user['id'] = content['pk']
            user['is_private'] = content['is_private']

            return user
        except ClientError as e:
            pc.printout('ClientError {0!s} (Code: {1:d}, Response: {2!s})'.format(e.code, e.error_response), pc.RED)
            error = json.loads(e.error_response)
            if 'message' in error:
                print(error['message'])
            if 'error_title' in error:
                print(error['error_title'])
            if 'challenge' in error:
                print("Please follow this link to complete the challenge: " + error['challenge']['url'])    
            sys.exit(2)
        

    def set_write_file(self, flag):
        if flag:
            pc.printout("Write to file: ")
            pc.printout("enabled", pc.GREEN)
            pc.printout("\n")
        else:
            pc.printout("Write to file: ")
            pc.printout("disabled", pc.RED)
            pc.printout("\n")

        self.writeFile = flag

    def set_json_dump(self, flag):
        if flag:
            pc.printout("Export to JSON: ")
            pc.printout("enabled", pc.GREEN)
            pc.printout("\n")
        else:
            pc.printout("Export to JSON: ")
            pc.printout("disabled", pc.RED)
            pc.printout("\n")

        self.jsonDump = flag

    def login(self, u, p):
        try:
            # if file session.json exists, load it, else dump it, the file should be in the root direcotry
            if os.path.isfile('session.json'):
                userSettings = client.load_settings('session.json')
                client.login_by_sessionid(userSettings["authorization_data"]["sessionid"])
                print("Loaded session from session.json")
            else:
                client.login(u, p)
                client.dump_settings('session.json')
            if os.path.isfile('session_loader.json'):
                loader.load_session_from_file(u, "session_loader.json")
            else:
                loader.login(u, p)  
                loader.save_session_to_file("session_loader.json")


        except ClientError as e:
            pc.printout('ClientError {0!s} (Code: {1:d}, Response: {2!s})'.format(e.msg, e.code, e.error_response), pc.RED)
            error = json.loads(e.error_response)
            pc.printout(error['message'], pc.RED)
            pc.printout(": ", pc.RED)
            
            pc.printout(e.msg, pc.RED)
            pc.printout("\n")
            if 'challenge' in error:
                print("Please follow this link to complete the challenge: " + error['challenge']['url'])
            exit(9)

    def to_json(self, python_object):
        if isinstance(python_object, bytes):
            return {'__class__': 'bytes',
                    '__value__': codecs.encode(python_object, 'base64').decode()}
        raise TypeError(repr(python_object) + ' is not JSON serializable')

    def from_json(self, json_object):
        if '__class__' in json_object and json_object['__class__'] == 'bytes':
            return codecs.decode(json_object['__value__'].encode(), 'base64')
        return json_object

    def check_following(self, username):
        if str(self.target_id) == str(client.user_id_from_username(username)):
            return True
        followingDict = client.user_following(client.user_id_from_username(username))
        for user in followingDict:
            print(user)
            if str(self.target_id) == user:
                return True
        return False

    def check_private_profile(self):
        if self.is_private and not self.following:
            pc.printout("Impossible to execute command: user has private profile\n", pc.RED)
            send = input("Do you want send a follow request? [Y/N]: ")
            if send.lower() == "y":
                client.user_follow(self.target_id)
                print("Sent a follow request to target. Use this command after target accepting the request.")

            return True
        return False

    def get_fwersemail(self):
        if self.check_private_profile():
            return

        _followers = []
        followersEmail = []


        pc.printout("Searching for emails of target followers... this can take a few minutes\n")

        data = client.user_followers(str(self.target_id))
        _followers.extend(data.values())
        for user in _followers:
            userDict = user.dict()
            userInfo = client.user_info_by_username(userDict['username']).dict()
            if 'email' in userDict and userDict['email']:
                u = {
                    'id': userDict['pk'],
                    'username': userDict['username'],
                    'full_name': userDict['full_name'],
                    'email': userInfo['public_email']
                }
                followersEmail.append(u)
            
        print("\n")
        
        if len(followersEmail) > 0:
            pc.printout("Do you want to get all emails? y/n: ", pc.YELLOW)
            value = input()
            
            if value == str("y") or value == str("yes") or value == str("Yes") or value == str("YES"):
                value = len(followersEmail)
            elif value == str(""):
                print("\n")
                return
            elif value == str("n") or value == str("no") or value == str("No") or value == str("NO"):
                while True:
                    try:
                        pc.printout("How many emails do you want to get? ", pc.YELLOW)
                        new_value = int(input())
                        value = new_value - 1
                        break
                    except ValueError:
                        pc.printout("Error! Please enter a valid integer!", pc.RED)
                        print("\n")
                        return
            else:
                pc.printout("Error! Please enter y/n :-)", pc.RED)
                print("\n")
                return

            t = PrettyTable(['ID', 'Username', 'Full Name', 'Email'])
            t.align["ID"] = "l"
            t.align["Username"] = "l"
            t.align["Full Name"] = "l"
            t.align["Email"] = "l"

            json_data = {}

            for node in followersEmail:
                t.add_row([str(node['id']), node['username'], node['full_name'], node['email']])

            if self.writeFile:
                file_name = self.output_dir + "/" + self.target + "_fwersemail.txt"
                file = open(file_name, "w")
                file.write(str(t))
                file.close()

            if self.jsonDump:
                json_data['followers_email'] = followersEmail
                json_file_name = self.output_dir + "/" + self.target + "_fwersemail.json"
                with open(json_file_name, 'w') as f:
                    json.dump(json_data, f)

            print(t)
        else:
            pc.printout("Sorry! No results found :-(\n", pc.RED)



    def get_fwingsemail(self):
        if self.check_private_profile():
            return

        _followings = []
        followingsEmail = []


        pc.printout("Searching for emails of target followers... this can take a few minutes\n")

        data = client.user_following(str(self.target_id))
        print(data)
        _followings.extend(data.values())
        for user in _followings:
            userDict = user.dict()
            userInfo = client.user_info_by_username(userDict['username']).dict()
            print(userInfo)
            if userInfo['public_email']:
                u = {
                    'id': userDict['pk'],
                    'username': userDict['username'],
                    'full_name': userDict['full_name'],
                    'email': userInfo['public_email']
                }
                followingsEmail.append(u)
            
        print("\n")
        
        if len(followingsEmail) > 0:
            pc.printout("Do you want to get all emails? y/n: ", pc.YELLOW)
            value = input()
            
            if value == str("y") or value == str("yes") or value == str("Yes") or value == str("YES"):
                value = len(followingsEmail)
            elif value == str(""):
                print("\n")
                return
            elif value == str("n") or value == str("no") or value == str("No") or value == str("NO"):
                while True:
                    try:
                        pc.printout("How many emails do you want to get? ", pc.YELLOW)
                        new_value = int(input())
                        value = new_value - 1
                        break
                    except ValueError:
                        pc.printout("Error! Please enter a valid integer!", pc.RED)
                        print("\n")
                        return
            else:
                pc.printout("Error! Please enter y/n :-)", pc.RED)
                print("\n")
                return

            t = PrettyTable(['ID', 'Username', 'Full Name', 'Email'])
            t.align["ID"] = "l"
            t.align["Username"] = "l"
            t.align["Full Name"] = "l"
            t.align["Email"] = "l"

            json_data = {}

            for node in followingsEmail:
                t.add_row([str(node['id']), node['username'], node['full_name'], node['email']])

            if self.writeFile:
                file_name = self.output_dir + "/" + self.target + "_fwingsemail.txt"
                file = open(file_name, "w")
                file.write(str(t))
                file.close()

            if self.jsonDump:
                json_data['followings_email'] = followingsEmail
                json_file_name = self.output_dir + "/" + self.target + "_fwingsemail.json"
                with open(json_file_name, 'w') as f:
                    json.dump(json_data, f)

            print(t)
        else:
            pc.printout("Sorry! No results found :-(\n", pc.RED)

    def get_fwingsnumber(self):
        if self.check_private_profile():
            return
       
        try:

            pc.printout("Searching for phone numbers of users followed by target... this can take a few minutes\n")

            followings = []

            rank_token = AppClient.generate_uuid()
            data = self.api.user_following(str(self.target_id), rank_token=rank_token)

            for user in data.get('users', []):
                u = {
                    'id': user['pk'],
                    'username': user['username'],
                    'full_name': user['full_name']
                }
                followings.append(u)

            next_max_id = data.get('next_max_id')
            
            while next_max_id:
                results = self.api.user_following(str(self.target_id), rank_token=rank_token, max_id=next_max_id)

                for user in results.get('users', []):
                    u = {
                        'id': user['pk'],
                        'username': user['username'],
                        'full_name': user['full_name']
                    }
                    followings.append(u)

                next_max_id = results.get('next_max_id')
       
            results = []
        
            pc.printout("Do you want to get all phone numbers? y/n: ", pc.YELLOW)
            value = input()
            
            if value == str("y") or value == str("yes") or value == str("Yes") or value == str("YES"):
                value = len(followings)
            elif value == str(""):
                print("\n")
                return
            elif value == str("n") or value == str("no") or value == str("No") or value == str("NO"):
                while True:
                    try:
                        pc.printout("How many phone numbers do you want to get? ", pc.YELLOW)
                        new_value = int(input())
                        value = new_value - 1
                        break
                    except ValueError:
                        pc.printout("Error! Please enter a valid integer!", pc.RED)
                        print("\n")
                        return
            else:
                pc.printout("Error! Please enter y/n :-)", pc.RED)
                print("\n")
                return

            for follow in followings:
                sys.stdout.write("\rCatched %i followings phone numbers" % len(results))
                sys.stdout.flush()
                user = self.api.user_info(str(follow['id']))
                if 'contact_phone_number' in user['user'] and user['user']['contact_phone_number']:
                    follow['contact_phone_number'] = user['user']['contact_phone_number']
                    if len(results) > value:
                        break
                    results.append(follow)

        except ClientThrottledError as e:
            pc.printout("\nError: Instagram blocked the requests. Please wait a few minutes before you try again.", pc.RED)
            pc.printout("\n")
        
        print("\n")

        if len(results) > 0:
            t = PrettyTable(['ID', 'Username', 'Full Name', 'Phone'])
            t.align["ID"] = "l"
            t.align["Username"] = "l"
            t.align["Full Name"] = "l"
            t.align["Phone number"] = "l"

            json_data = {}

            for node in results:
                t.add_row([str(node['id']), node['username'], node['full_name'], node['contact_phone_number']])

            if self.writeFile:
                file_name = self.output_dir + "/" + self.target + "_fwingsnumber.txt"
                file = open(file_name, "w")
                file.write(str(t))
                file.close()

            if self.jsonDump:
                json_data['followings_phone_numbers'] = results
                json_file_name = self.output_dir + "/" + self.target + "_fwingsnumber.json"
                with open(json_file_name, 'w') as f:
                    json.dump(json_data, f)

            print(t)
        else:
            pc.printout("Sorry! No results found :-(\n", pc.RED)

    def get_fwersnumber(self):
        if self.check_private_profile():
            return

        followings = []

        try:

            pc.printout("Searching for phone numbers of users followers... this can take a few minutes\n")


            rank_token = AppClient.generate_uuid()
            data = self.api.user_following(str(self.target_id), rank_token=rank_token)

            for user in data.get('users', []):
                u = {
                    'id': user['pk'],
                    'username': user['username'],
                    'full_name': user['full_name']
                }
                followings.append(u)

            next_max_id = data.get('next_max_id')
            
            while next_max_id:
                results = self.api.user_following(str(self.target_id), rank_token=rank_token, max_id=next_max_id)

                for user in results.get('users', []):
                    u = {
                        'id': user['pk'],
                        'username': user['username'],
                        'full_name': user['full_name']
                    }
                    followings.append(u)

                next_max_id = results.get('next_max_id')
        
            results = []
            
            pc.printout("Do you want to get all phone numbers? y/n: ", pc.YELLOW)
            value = input()
            
            if value == str("y") or value == str("yes") or value == str("Yes") or value == str("YES"):
                value = len(followings)
            elif value == str(""):
                print("\n")
                return
            elif value == str("n") or value == str("no") or value == str("No") or value == str("NO"):
                while True:
                    try:
                        pc.printout("How many phone numbers do you want to get? ", pc.YELLOW)
                        new_value = int(input())
                        value = new_value - 1
                        break
                    except ValueError:
                        pc.printout("Error! Please enter a valid integer!", pc.RED)
                        print("\n")
                        return
            else:
                pc.printout("Error! Please enter y/n :-)", pc.RED)
                print("\n")
                return

            for follow in followings:
                sys.stdout.write("\rCatched %i followers phone numbers" % len(results))
                sys.stdout.flush()
                user = self.api.user_info(str(follow['id']))
                if 'contact_phone_number' in user['user'] and user['user']['contact_phone_number']:
                    follow['contact_phone_number'] = user['user']['contact_phone_number']
                    if len(results) > value:
                        break
                    results.append(follow)

        except ClientThrottledError as e:
            pc.printout("\nError: Instagram blocked the requests. Please wait a few minutes before you try again.", pc.RED)
            pc.printout("\n")

        print("\n")

        if len(results) > 0:
            t = PrettyTable(['ID', 'Username', 'Full Name', 'Phone'])
            t.align["ID"] = "l"
            t.align["Username"] = "l"
            t.align["Full Name"] = "l"
            t.align["Phone number"] = "l"

            json_data = {}

            for node in results:
                t.add_row([str(node['id']), node['username'], node['full_name'], node['contact_phone_number']])

            if self.writeFile:
                file_name = self.output_dir + "/" + self.target + "_fwersnumber.txt"
                file = open(file_name, "w")
                file.write(str(t))
                file.close()

            if self.jsonDump:
                json_data['followings_phone_numbers'] = results
                json_file_name = self.output_dir + "/" + self.target + "_fwerssnumber.json"
                with open(json_file_name, 'w') as f:
                    json.dump(json_data, f)

            print(t)
        else:
            pc.printout("Sorry! No results found :-(\n", pc.RED)

    def get_comments(self):
        if self.check_private_profile():
            return

        pc.printout("Searching for users who commented...\n")

        data = self.__get_feed__()
        users = []

        for post in data:
            comments = self.__get_comments__(post['id'])
            for comment in comments:
                print(comment['text'])
                
                # if not any(u['id'] == comment['user']['pk'] for u in users):
                #     user = {
                #         'id': comment['user']['pk'],
                #         'username': comment['user']['username'],
                #         'full_name': comment['user']['full_name'],
                #         'counter': 1
                #     }
                #     users.append(user)
                # else:
                #     for user in users:
                #         if user['id'] == comment['user']['pk']:
                #             user['counter'] += 1
                #             break

        if len(users) > 0:
            ssort = sorted(users, key=lambda value: value['counter'], reverse=True)

            json_data = {}

            t = PrettyTable()

            t.field_names = ['Comments', 'ID', 'Username', 'Full Name']
            t.align["Comments"] = "l"
            t.align["ID"] = "l"
            t.align["Username"] = "l"
            t.align["Full Name"] = "l"

            for u in ssort:
                t.add_row([str(u['counter']), u['id'], u['username'], u['full_name']])

            print(t)

            if self.writeFile:
                file_name = self.output_dir + "/" + self.target + "_users_who_commented.txt"
                file = open(file_name, "w")
                file.write(str(t))
                file.close()

            if self.jsonDump:
                json_data['users_who_commented'] = ssort
                json_file_name = self.output_dir + "/" + self.target + "_users_who_commented.json"
                with open(json_file_name, 'w') as f:
                    json.dump(json_data, f)
        else:
            pc.printout("Sorry! No results found :-(\n", pc.RED)
