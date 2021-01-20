import os
import sys 
from shotgun_api3 import Shotgun
from datetime import datetime

import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.NullHandler())

# connection to server
server = 'https://pts.shotgunstudio.com'
script = 'ptTools'
id = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
sg = Shotgun(server, script, id)

def setShotgunData(project, episode, sequence, shot, taskName, status, versionName, framePath, description='', user=''): 
	""" create task or layer name """ 

	projectEntity = sg.find_one('Project', [['name', 'is', project]], ['id'])
	
	shotFilters = [['project', 'is', projectEntity], 
					['sg_scene.Scene.code', 'is', episode], 
					['sg_sequence.Sequence.code', 'is', sequence], 
					['code', 'is', shot]]
	shotEntity = sg.find_one('Shot', shotFilters, ['id', 'code'])

	if shotEntity: 
		# find if task exists 
		filters = [['project', 'is', projectEntity], 
					['entity', 'is', shotEntity], 
					['step.Step.id', 'is', 43], 
					['content', 'is', taskName]]
		taskEntity = sg.find_one('Task', filters, ['id', 'code'])
		stepEntity = sg.find_one('Step', [['code', 'is', 'Render']], ['id', 'code'])

		# create task if not exists 
		if not taskEntity: 
			logger.info('Task not exists, create new task')

			data = { 'project': projectEntity, 
					'entity': shotEntity,
					'content': taskName, 
					'step': stepEntity, 
					'sg_status_list': status, 
					'sg_hero_2': {'local_path': '%s\\' % framePath.replace('/', '\\'), 'name': os.path.basename(framePath)}
					}
			taskEntity = sg.create('Task', data)
			logger.info(taskEntity)

		# if exists, update 
		else: 
			logger.info('Task exists, update existing task')

			data = {'sg_status_list': status, 
					'sg_hero_2': {'local_path': '%s\\' % framePath.replace('/', '\\'), 'name': os.path.basename(framePath)}}
			taskEntity = sg.update('Task', taskEntity['id'], data)
			logger.info(taskEntity)


		# create playlist 
		playlistEntity = sgCreatePlaylistByDate(project, 'render')

		userEntity=dict()
		if user=='':
			userEntity = {'type': 'ApiUser', 'id': 84}
		else:
			userEntity = sg.find_one('HumanUser', [['name', 'is', user]], ['id'])
			print userEntity

		# create version 
		versionData = {'code': versionName, 
						'project': projectEntity, 
						'entity': shotEntity, 
						'sg_task': taskEntity, 
						'sg_path_to_frames': framePath, 
						'playlists': [playlistEntity],
						'user': userEntity
						}

		if description: 
			versionData.update({'description': description})
		versionEntity = sg.create('Version', versionData)
		logger.info('Version created')
		logger.info(versionEntity)

	else: 
		# shot not found 
		logger.info('shot not found')


def sgCreatePlaylistByDate(projectName, taskName, extra='') : 
	proj = sg.find_one('Project', [['name', 'is', projectName]], ['name', 'sg_projcode'])
	playlistName = '%s_%s_%s' % (proj['sg_projcode'], taskName, str(datetime.now()).split(' ')[0])
	if extra : 
		playlistName = '%s_%s_%s_%s' % (proj['sg_projcode'], taskName, extra, str(datetime.now()).split(' ')[0])
	playlist = sg.find_one('Playlist', [['code', 'is', playlistName]], ['code'])

	if not playlist : 
		data = {'project': proj, 'code': playlistName}
		playlist = sg.create('Playlist', data)

	return playlist 