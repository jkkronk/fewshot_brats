__author__ = 'jonatank'
from torch.utils.data import Dataset
from torchvision import transforms

import h5py
import torch
import numpy as np
from skimage.transform import resize
import pickle
import random
from PIL import Image
from imgaug import augmenters as iaa
from imgaug.augmentables.segmaps import SegmentationMapsOnImage
import time
import imgaug as ia

class camcan_dataset(Dataset):
    def __init__(self, data_path, train, img_size, data_aug=0):
        self.img_size = img_size
        self.aug = data_aug
        path = (data_path + 'camcan_t2_train_set_4.hdf5') if train else (data_path + 'camcan_t2_val_set_4.hdf5')

        self.data = h5py.File(path, 'r')
        # Set size of dataset
        self.size = len(self.data['Scan'])

    def transform(self, img):
        # Function for data augmentation
        # 1) Affine Augmentations: Rotation (-15 to +15 degrees), Scaling, Flipping.
        # 2) Elastic deformations
        # 3) Intensity augmentations

        ia.seed(int(time.time())) # Seed for random augmentations

        # Needed for iaa
        img = (img*255).astype('uint8')

        if self.aug: # Augmentation only performed on train set
            img = np.expand_dims(img, axis=0)

            seq_all = iaa.Sequential([
                #iaa.Fliplr(0.5), # Horizontal flips
                iaa.ElasticTransformation(alpha=(0.0, 10.0), sigma=4.0),  # Elastic
                iaa.LinearContrast((0.85, 1.15)),  # Contrast
                iaa.Multiply((0.85, 1.15), per_channel=1),
                iaa.blur.AverageBlur(k=(0, 2))  # Gausian blur
            ], random_order=True)

            images_aug = seq_all(images=img) # Intensity and contrast only on input image

            img = np.squeeze(images_aug, axis=0)

        flip_tensor_trans = transforms.Compose([
            transforms.ToTensor()
        ])

        return flip_tensor_trans(img)

    def __getitem__(self, index):
        data_img = self.data['Scan'][index].reshape(200,200)

        # Resize Images to network
        data_img = resize(data_img, (self.img_size, self.img_size))

        # Expand to data with channel [1,128,128]
        data_img = np.expand_dims(data_img, axis=-1)

        img_trans = self.transform(data_img)

        mask = torch.zeros(img_trans.size())
        mask[img_trans > 0] = 1

        return img_trans, mask

    def __len__(self):
        return self.size

class brats_dataset(Dataset):
    def __init__(self, data_path, dataset, img_size, prop_subjects=1, rand_subj = True, use_aug = False):
        self.img_size = img_size
        self.prop_subjects = prop_subjects
        self.dataset = dataset
        self.aug = use_aug
        # Open datasets
        if self.dataset == 'train':
            self.train = True
            print('Loading train set')
            self.path = (data_path + 'brats17_t2_train.hdf5')
            f = open(data_path + 'subj_t2_dict.pkl','rb')
        elif self.dataset == 'valid':
            self.train = False
            print('Loading validation set')
            self.path = (data_path + 'brats17_t2_val.hdf5')
            f = open(data_path + 'subj_t2_valid_dict.pkl','rb')
        elif self.dataset == 'test':
            self.train = False
            print('Loading test set')
            self.path = (data_path + 'brats17_t2_test.hdf5')
            f = open(data_path + 'subj_t2_test_dict.pkl','rb')
        else:
            print('No set named ' + set)
            exit()

        subj_dict = pickle.load(f)
        f.close()

        # Get subject list
        key_list_len = len(list(subj_dict.keys()))
        keys = list(subj_dict.keys())

        if rand_subj: #Shuffle list of subjects
            random.shuffle(keys)

            # Take prop numbers of subjects
        nbr_subj = int(key_list_len*self.prop_subjects) if int(key_list_len*self.prop_subjects) > 1 else 1
        key_list = keys[:nbr_subj]

        self.keys = key_list

        # Set size of dataset and get slices
        self.size = 0
        subj_slices = []
        for subj_key in key_list:
            self.size += len(subj_dict[subj_key])
            subj_slices.extend(subj_dict[subj_key])

        # Load hdf5 file
        self.data = h5py.File(self.path, 'r')

        # Init data arrays
        self.data_img = np.zeros((self.size, 200, 200))
        self.seg_img = np.zeros((self.size, 200, 200), dtype='bool')

        # Iterate slices and place in arrays
        for idx, id_slice in enumerate(subj_slices):
            self.data_img[idx] = self.data['Scan'][id_slice].reshape(200,200)
            self.seg_img[idx] = self.data['Seg'][id_slice].reshape(200,200)

    def transform(self, img, seg):
        # Function for data augmentation
        # 1) Affine Augmentations: Rotation (-15 to +15 degrees), Scaling, Flipping.
        # 2) Elastic deformations
        # 3) Intensity augmentations

        ia.seed(int(time.time())) # Seed for random augmentations

        # Needed for iaa
        img = (img*255).astype('uint8')
        seg = (seg).astype('uint8')

        if self.aug: # Augmentation only performed on train set
            img = np.expand_dims(img, axis=0)
            segmap = SegmentationMapsOnImage(seg, shape=img.shape[1:]) # Create segmentation map

            seq_all = iaa.Sequential([
                iaa.Fliplr(0.5), # Horizontal flips
                iaa.Affine(
                    scale={"x": (0.9, 1.1), "y": (0.9, 1.1)},
                    translate_percent={"x": (0, 0), "y": (0, 0)},
                    rotate=(-15, 15),
                    shear=(0, 0)), # Scaling, rotating
                iaa.ElasticTransformation(alpha=10, sigma=10) # Elastic
                ], random_order=True)

            seq_img = iaa.Sequential([
                iaa.LinearContrast((0.95, 1.05)), # Contrast
                iaa.Multiply((0.9, 1.1), per_channel=1), # Intensity
                ], random_order=True)

            images_aug = seq_img(images=img) # Intensity and contrast only on input image
            img, seg = seq_all(images=images_aug, segmentation_maps=segmap) # Rest of augmentations

            img = np.squeeze(img, axis=0)
            # Get segmentation map
            seg = seg.draw(size=img.shape)[0]
            seg = seg[:,:,0]
            seg[seg > 0] = 1

        # To PIL for Flip and ToTensor
        img_PIL = Image.fromarray(img)
        seg_PIL = Image.fromarray(seg*255)

        flip_tensor_trans = transforms.Compose([
            transforms.RandomVerticalFlip(p=1), # Flipped due to camcan
            transforms.ToTensor()
        ])

        return flip_tensor_trans(img_PIL), flip_tensor_trans(seg_PIL)


    def __getitem__(self, index):
        # Resize Images to network
        img_data = resize(self.data_img[index], (self.img_size, self.img_size))
        seg_data = resize(self.seg_img[index], (self.img_size, self.img_size))

        # Set all segmented elements to 1
        seg_data[seg_data > 0] = 1

        img_trans, seg_trans = self.transform(img_data, seg_data)

        mask = torch.zeros(img_trans.size())
        mask[img_trans > 0] = 1

        return img_trans, seg_trans, mask

    def __len__(self):
        return self.size

class brats_dataset_subj(Dataset):
    def __init__(self, data_path, dataset, img_size, slices, use_aug=False):
        self.img_size = img_size
        self.slices = slices
        self.dataset = dataset
        self.aug = use_aug

        # Open datasets
        if self.dataset == 'train':
            self.train = True
            print('Loading train set for subj')
            self.path = (data_path + 'brats17_t2_train.hdf5')
        elif self.dataset == 'valid':
            self.train = False
            print('Loading validation set for subj')
            self.path = (data_path + 'brats17_t2_val.hdf5')
        elif self.dataset == 'test':
            self.train = False
            print('Loading test set for subj')
            self.path = (data_path + 'brats17_t2_test.hdf5')
        else:
            print('No set named ' + set)
            exit()

        # Get subject list
        self.size = len(slices)

        # Load hdf5 file
        with h5py.File(self.path, 'r') as f:
            d = f

            # torch first saves this numpy array as a regular tensor and share_memory_() then copies it again to
            # a shared memory location. Therefore at least twice the size of the dataset / numpy matrix is needed
            # for memory.

            # Init data arrays
            self.data_img = np.zeros((self.size, 200, 200))
            self.seg_img = np.zeros((self.size, 200, 200), dtype='bool')

            # Iterate slices and place in arrays
            for idx, id_slice in enumerate(slices):
                self.data_img[idx] = torch.from_numpy(d.get('Scan')[id_slice].reshape(200, 200)).share_memory_()
                #self.data['Scan'][id_slice].reshape(200, 200)
                self.seg_img[idx] = torch.from_numpy(d.get('Seg')[id_slice].reshape(200, 200).astype(np.bool)).share_memory_()
                #self.data['Seg'][id_slice].reshape(200, 200)

            f.close()

    def transform(self, img, seg):
        # Function for data augmentation
        # 1) Affine Augmentations: Rotation (-15 to +15 degrees), Scaling, Flipping.
        # 2) Elastic deformations
        # 3) Intensity augmentations

        ia.seed(int(time.time()))  # Seed for random augmentations

        # Needed for iaa
        img = (img * 255).astype('uint8')
        seg = (seg).astype('uint8')

        if self.aug:  # Augmentation only performed on train set
            img = np.expand_dims(img, axis=0)
            segmap = SegmentationMapsOnImage(seg, shape=img.shape[1:])  # Create segmentation map

            seq_all = iaa.Sequential([
                iaa.Fliplr(0.5),  # Horizontal flips
                iaa.Affine(
                    scale={"x": (0.85, 1.15), "y": (0.85, 1.15)},
                    translate_percent={"x": (0, 0), "y": (0, 0)},
                    rotate=(-15, 15),
                    shear=(0, 0)),  # Scaling, rotating
                iaa.ElasticTransformation(alpha=(0.0, 10.0), sigma=4.0)  # Elastic
            ], random_order=True)

            seq_img = iaa.Sequential([
                iaa.blur.AverageBlur(k=(0, 2)),  # Gausian blur
                iaa.LinearContrast((0.85, 1.15)),  # Contrast
                iaa.Multiply((0.85, 1.15), per_channel=1),  # Intensity
            ], random_order=True)

            img, seg = seq_all(images=img, segmentation_maps=segmap)  # Rest of augmentations

            mask = np.zeros(img.shape) # Create mask
            mask[img > 0] = 1

            img = seq_img(images=img)  # Intensity and contrast only on input image

            img = np.squeeze(img, axis=0)
            mask = np.squeeze(mask,axis=0)

            # Get segmentation map
            seg = seg.draw(size=img.shape)[0]
            seg = seg[:, :, 0]
            seg[seg > 0] = 1
        else:
            mask = np.zeros(img.shape)
            mask[img > 0] = 1

        # To PIL for Flip and ToTensor
        img_PIL = Image.fromarray(img)
        seg_PIL = Image.fromarray(seg * 255)
        mask_PIL = Image.fromarray(mask * 255)

        flip_tensor_trans = transforms.Compose([
            transforms.RandomVerticalFlip(p=1),  # Flipped due to camcan
            transforms.ToTensor()
        ])

        return flip_tensor_trans(img_PIL), flip_tensor_trans(seg_PIL), flip_tensor_trans(mask_PIL)

    def __getitem__(self, index):
        # Resize Images to network
        img_data = resize(self.data_img[index], (self.img_size, self.img_size))
        seg_data = resize(self.seg_img[index], (self.img_size, self.img_size))

        # Set all segmented elements to 1
        seg_data[seg_data > 0] = 1

        img_trans, seg_trans, mask_trans = self.transform(img_data, seg_data)

        return img_trans, seg_trans, mask_trans

    def __len__(self):
        return self.size

class brats_dataset_subj_teacher(Dataset):
    def __init__(self, data_path, dataset, img_size, slices, use_aug=False):
        self.img_size = img_size
        self.slices = slices
        self.dataset = dataset
        self.aug = use_aug

        # Open datasets
        if self.dataset == 'train':
            self.train = True
            print('Loading train set for subj')
            self.path = (data_path + 'brats17_t2_train.hdf5')
        elif self.dataset == 'valid':
            self.train = False
            print('Loading validation set for subj')
            self.path = (data_path + 'brats17_t2_val.hdf5')
        elif self.dataset == 'test':
            self.train = False
            print('Loading test set for subj')
            self.path = (data_path + 'brats17_t2_test.hdf5')
        else:
            print('No set named ' + set)
            exit()

        # Get subject list
        self.size = len(slices)

        # Load hdf5 file
        self.data = h5py.File(self.path, 'r')

        # Init data arrays
        self.data_img = np.zeros((self.size, 200, 200))
        self.seg_img = np.zeros((self.size, 200, 200), dtype='bool')

        # Iterate slices and place in arrays
        for idx, id_slice in enumerate(slices):
            self.data_img[idx] = self.data['Scan'][id_slice].reshape(200, 200)
            self.seg_img[idx] = self.data['Seg'][id_slice].reshape(200, 200)

    def transform(self, img, seg):
        # Function for data augmentation
        # 1) Affine Augmentations: Rotation (-15 to +15 degrees), Scaling, Flipping.
        # 2) Elastic deformations
        # 3) Intensity augmentations

        ia.seed(int(time.time()))  # Seed for random augmentations

        # Needed for iaa
        img = (img * 255).astype('uint8')
        seg = (seg).astype('uint8')

        if self.aug:  # Augmentation only performed on train set
            img = np.expand_dims(img, axis=0)
            segmap = SegmentationMapsOnImage(seg, shape=img.shape[1:])  # Create segmentation map

            seq_all = iaa.Sequential([
                iaa.Fliplr(0.5),  # Horizontal flips
                iaa.Affine(
                    scale={"x": (0.9, 1.1), "y": (0.9, 1.1)},
                    translate_percent={"x": (0, 0), "y": (0, 0)},
                    rotate=(-15, 15),
                    shear=(0, 0)),  # Scaling, rotating
                iaa.ElasticTransformation(alpha=10, sigma=10)  # Elastic
            ], random_order=True)

            seq_img = iaa.Sequential([
                iaa.LinearContrast((0.95, 1.05)),  # Contrast
                iaa.Multiply((0.9, 1.1), per_channel=1),  # Intensity
            ], random_order=True)

            images_aug = seq_img(images=img)  # Intensity and contrast only on input image
            img, seg = seq_all(images=images_aug, segmentation_maps=segmap)  # Rest of augmentations

            img = np.squeeze(img, axis=0)
            # Get segmentation map
            seg = seg.draw(size=img.shape)[0]
            seg = seg[:, :, 0]
            seg[seg > 0] = 1

        # To PIL for Flip and ToTensor
        img_PIL = Image.fromarray(img)
        seg_PIL = Image.fromarray(seg * 255)

        flip_tensor_trans = transforms.Compose([
            transforms.RandomVerticalFlip(p=1),  # Flipped due to camcan
            transforms.ToTensor()
        ])

        return flip_tensor_trans(img_PIL), flip_tensor_trans(seg_PIL)

    def __getitem__(self, index):
        # Resize Images to network
        img_data = resize(self.data_img[index], (self.img_size, self.img_size))
        seg_data = resize(self.seg_img[index], (self.img_size, self.img_size))

        # Set all segmented elements to 1
        seg_data[seg_data > 0] = 1

        img_trans, seg_trans = self.transform(img_data, seg_data)

        img_trans_teacher, seg_trans_teacher = self.transform(img_data, seg_data)


        mask = torch.zeros(img_trans.size())
        mask[img_trans > 0] = 1

        mask_teacher = torch.zeros(img_trans_teacher.size())
        mask_teacher[img_trans_teacher > 0] = 1

        return img_trans, seg_trans, mask, img_trans_teacher, seg_trans_teacher, mask_teacher

    def __len__(self):
        return self.size