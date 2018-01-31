from __future__ import print_function
from dataset import Dataset
import os
from inspect import currentframe, getframeinfo
from loggers import Log
import pandas as pd
import cv2
import dlib
import numpy as np

class CelebAAlignedDataset(Dataset):
    """Class that abstracs celeba aligned dataset.
    Assumtions
        - Dataset contains images inside dataset_dir
        - list_attr_celeba.txt inside dataset_dir
        - list_landmarks_align_celeba.txt inside dataset_dir
    Parameters
    ----------
    dataset_dir : str
        Relative or absolute path to dataset folder
    Raises
    AssertionError 
        if the dataset path does not exist.
    """

    def __init__(self,dataset_dir,image_shape=(227,227,3),labels=["Smiling","Male"]):
        super(CelebAAlignedDataset,self).__init__(dataset_dir,image_shape)
        self.labels = labels
        self.detector = dlib.get_frontal_face_detector()
    def load_dataset(self):
        if set(self.labels).issubset(["Smiling","Mal"]):
            if self.contain_dataset_files():
                self.train_dataset = self.get_meta(os.path.join(self.dataset_dir,"train.pkl"))
                self.test_dataset = self.get_meta(os.path.join(self.dataset_dir,"test.pkl"))
                if os.path.exists(os.path.join(self.dataset_dir,"validation.pkl")):
                    self.validation_dataset = self.get_meta(os.path.join(self.dataset_dir,"validation.pkl"))
                else:
                    self.validation_dataset = None
                    frameinfo = getframeinfo(currentframe())
                    Log.WARNING("Unable to find validation dataset",file_name=__name__,line_number=frameinfo.lineno)
            self.train_dataset = self.fix_labeling_issue(self.train_dataset)
            self.test_dataset = self.fix_labeling_issue(self.test_dataset)
            self.validation_dataset = self.fix_labeling_issue(self.validation_dataset)
            self.test_dataset_images = self.load_images(self.test_dataset)
            self.validation_dataset_images = self.load_dataset(self.validation_dataset)
            self.dataset_loaded = True
        else:
            raise NotImplementedError("Not implemented for labels:"+str(self.labels))
    def load_images(self,dataframe):
        if dataframe is None:
            return None
        else:
            assert type(dataframe) == pd.core.frame.DataFrame, "argument to load image should be dataframe"
            assert  "file_location" in dataframe.columns, "dataframe should contain file_location column"
            output_images = np.zeros((len(dataframe),self.image_shape[0],self.image_shape[1],self.image_shape[2]))
            for index,row in dataframe.iterrows():
                img = cv2.imread(os.path.join(self.dataset_dir,row["file_location"]))

                if img is None:
                    Log.WARNING("Unable to read images from "+os.path.join(self.dataset_dir,row["file_location"]))
                    continue
                faces = self.detector(img)
                if(len(faces)>0):
                    face_location = faces[0]
                    face_image = img[face_location.top():face_location.bottom(),face_location.left():face_location.right()]
                    face_image = cv2.resize(face_image,(self.image_shape[0],self.image_shape[1])).astype("float32")
                    output_images[index] = face_image
                else:
                    face_image = cv2.resize(img,(self.image_shape[0],self.image_shape[1])).astype("float32")
                    output_images[index] = face_image
                    Log.WARNING("Dlib unable to find faces from :"+os.path.join(self.dataset_dir,row["file_location"])+" Loading full image as face")
            return output_images
    def meet_convention(self):
        if self.contain_dataset_files():
            return
        elif os.path.exist(os.path.join(self.dataset_dir,"all.pkl")):
            dataframe = pd.read_pickle(os.path.join(self.dataset_dir,"all.pkl"))
            train,test,validation = self.split_train_test_validation(dataframe)
            train.to_pickle(os.path.join(self.dataset_dir,"train.pkl"))      
            test.to_pickle(os.path.join(self.dataset_dir,"test.pkl"))      
            validation.to_pickle(os.path.join(self.dataset_dir,"validation.pkl"))
        else:
            dataframe = self.load_dataset_from_annotation_file()
            train,test,validation = self.split_train_test_validation(dataframe)
            train.to_pickle(os.path.join(self.dataset_dir,"train.pkl"))      
            test.to_pickle(os.path.join(self.dataset_dir,"test.pkl"))      
            validation.to_pickle(os.path.join(self.dataset_dir,"validation.pkl"))      
            dataframe.to_pickle(os.path.join(self.dataset_dir,"all.pkl"))

    def load_dataset_from_annotation_file(self):
        annotation_file = os.path.join(self.dataset_dir,"list_attr_celeba.txt")
        headers = ['imgfile', '5_o_Clock_Shadow', 'Arched_Eyebrows', 'Attractive', 'Bags_Under_Eyes', 'Bald', 'Bangs', 'Big_Lips', 'Big_Nose', 'Black_Hair', 'Blond_Hair', 'Blurry', 'Brown_Hair', 'Bushy_Eyebrows', 'Chubby', 'Double_Chin', 'Eyeglasses', 'Goatee', 'Gray_Hair', 'Heavy_Makeup', 'High_Cheekbones', 'Male', 'Mouth_Slightly_Open', 'Mustache', 'Narrow_Eyes', 'No_Beard', 'Oval_Face', 'Pale_Skin', 'Pointy_Nose', 'Receding_Hairline', 'Rosy_Cheeks', 'Sideburns', 'Smiling', 'Straight_Hair', 'Wavy_Hair', 'Wearing_Earrings', 'Wearing_Hat', 'Wearing_Lipstick', 'Wearing_Necklace', 'Wearing_Necktie', 'Young']
        df = pd.read_csv(annotation_file,sep= "\s+|\t+|\s+\t+|\t+\s+",names=headers,header=1)
        return df
    def generator(self,batch_size=32):
        while True:
            indexes = np.arange(len(self.train_dataset))
            np.random.shuffle(indexes)
            for i in range(0,len(indexes),batch_size):
                current_indexes = indexes[i:i+batch_size]
                current_dataframe = self.train_dataset.iloc[current_indexes].reset_index(drop=True)
                current_images = self.load_images(current_dataframe)
                X = current_images.astype(np.float32)/255
                smile = current_dataframe["Smiling"].as_matrix()
                yield X,smile
    def fix_labeling_issue(self,dataset):
        if dataset is None:
            return None
        output = dataset.copy(deep=True)
        for label in self.labels:
            output[label] = output[label]/2.0 + 1/2.0
        return output

