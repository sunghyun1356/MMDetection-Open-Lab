import copy
import os.path as osp
import unittest

from mmcv.transforms import Compose

from mmdet.datasets.transforms import MultiBranch
from mmdet.utils import register_all_modules

register_all_modules()


class TestMultiBranch(unittest.TestCase):

    def setUp(self):
        """Setup the model and optimizer which are used in every test method.

        TestCase calls functions in this order: setUp() -> testMethod() ->
        tearDown() -> cleanUp()
        """
        data_prefix = osp.join(osp.dirname(__file__), '../../data')
        img_path = osp.join(data_prefix, 'color.jpg')
        seg_map = osp.join(data_prefix, 'gray.jpg')
        self.meta_keys = ('img_id', 'img_path', 'ori_shape', 'img_shape',
                          'scale_factor', 'flip', 'flip_direction',
                          'homography_matrix')
        self.results = {
            'img_path':
            img_path,
            'img_id':
            12345,
            'img_shape': (300, 400),
            'seg_map_path':
            seg_map,
            'instances': [{
                'bbox': [0, 0, 10, 20],
                'bbox_label': 1,
                'mask': [[0, 0, 0, 20, 10, 20, 10, 0]],
                'ignore_flag': 0
            }, {
                'bbox': [10, 10, 110, 120],
                'bbox_label': 2,
                'mask': [[10, 10, 110, 10, 110, 120, 110, 10]],
                'ignore_flag': 0
            }, {
                'bbox': [50, 50, 60, 80],
                'bbox_label': 2,
                'mask': [[50, 50, 60, 50, 60, 80, 50, 80]],
                'ignore_flag': 1
            }]
        }
        self.weak_pipeline = [
            dict(type='ShearX'),
            dict(type='PackDetInputs', meta_keys=self.meta_keys)
        ]
        self.strong_pipeline = [
            dict(type='ShearX'),
            dict(type='ShearY'),
            dict(type='PackDetInputs', meta_keys=self.meta_keys)
        ]
        self.labeled_pipeline = [
            dict(type='LoadImageFromFile'),
            dict(
                type='LoadAnnotations',
                with_bbox=True,
                with_mask=True,
                with_seg=True),
            dict(type='Resize', scale=(1333, 800), keep_ratio=True),
            dict(type='RandomFlip', prob=0.5),
            dict(
                type='MultiBranch',
                sup_teacher=self.weak_pipeline,
                sup_student=self.strong_pipeline),
        ]
        self.unlabeled_pipeline = [
            dict(type='LoadImageFromFile'),
            dict(type='Resize', scale=(1333, 800), keep_ratio=True),
            dict(type='RandomFlip', prob=0.5),
            dict(
                type='MultiBranch',
                unsup_teacher=self.weak_pipeline,
                unsup_student=self.strong_pipeline),
        ]

    def test_transform(self):
        labeled_pipeline = Compose(self.labeled_pipeline)
        labeled_results = labeled_pipeline(copy.deepcopy(self.results))
        unlabeled_pipeline = Compose(self.unlabeled_pipeline)
        unlabeled_results = unlabeled_pipeline(copy.deepcopy(self.results))

        # test branch sup_teacher and sup_student
        sup_branches = ['sup_teacher', 'sup_student']
        for branch in sup_branches:
            self.assertIn(branch, labeled_results)
            self.assertIn('homography_matrix',
                          labeled_results[branch]['data_sample'])
            self.assertIn('labels',
                          labeled_results[branch]['data_sample'].gt_instances)
            self.assertIn('bboxes',
                          labeled_results[branch]['data_sample'].gt_instances)
            self.assertIn('masks',
                          labeled_results[branch]['data_sample'].gt_instances)
            self.assertIn('gt_sem_seg', labeled_results[branch]['data_sample'])

        # test branch unsup_teacher and unsup_student
        unsup_branches = ['unsup_teacher', 'unsup_student']
        for branch in unsup_branches:
            self.assertIn(branch, unlabeled_results)
            self.assertIn('homography_matrix',
                          unlabeled_results[branch]['data_sample'])
            self.assertNotIn(
                'labels',
                unlabeled_results[branch]['data_sample'].gt_instances)
            self.assertNotIn(
                'bboxes',
                unlabeled_results[branch]['data_sample'].gt_instances)
            self.assertNotIn(
                'masks', unlabeled_results[branch]['data_sample'].gt_instances)
            self.assertNotIn('gt_sem_seg',
                             unlabeled_results[branch]['data_sample'])

    def test_repr(self):
        pipeline = [dict(type='PackDetInputs', meta_keys=())]
        transform = MultiBranch(sup=pipeline, unsup=pipeline)
        self.assertEqual(
            repr(transform),
            ("MultiBranch(branch_pipelines=['sup', 'unsup'])"))
