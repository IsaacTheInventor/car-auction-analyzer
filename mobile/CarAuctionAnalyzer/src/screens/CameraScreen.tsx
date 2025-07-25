import React, { useState, useEffect, useRef } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  Image,
  ScrollView,
  Alert,
  ActivityIndicator,
  Platform,
  StatusBar,
  SafeAreaView,
  Dimensions,
} from 'react-native';
import { Camera, CameraType, FlashMode } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import * as MediaLibrary from 'expo-media-library';
import * as FileSystem from 'expo-file-system';
import { MaterialIcons, Ionicons, FontAwesome5 } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { manipulateAsync, SaveFormat } from 'expo-image-manipulator';
import uuid from 'react-native-uuid';
import { apiClient, API_CONFIG } from '../config/api';

// Define the photo categories
enum PhotoCategory {
  EXTERIOR_FRONT = 'Exterior Front',
  EXTERIOR_REAR = 'Exterior Rear',
  EXTERIOR_DRIVER = 'Exterior Driver Side',
  EXTERIOR_PASSENGER = 'Exterior Passenger Side',
  INTERIOR_DASHBOARD = 'Interior Dashboard',
  INTERIOR_SEATS = 'Interior Seats',
  DAMAGE_AREA = 'Damage Area',
  OTHER = 'Other',
}

// Photo object interface
interface Photo {
  id: string;
  uri: string;
  category: PhotoCategory;
  timestamp: Date;
}

// Vehicle metadata interface
interface VehicleMetadata {
  make?: string;
  model?: string;
  year?: number;
  vin?: string;
  auction_id?: string;
  auction_url?: string;
  asking_price?: number;
  notes?: string;
}

// Navigation params
type RootStackParamList = {
  Camera: undefined;
  VehicleForm: { photos: Photo[] };
  AnalysisResults: { vehicleId: string; taskId: string };
};

type CameraScreenNavigationProp = StackNavigationProp<RootStackParamList, 'Camera'>;

const CameraScreen: React.FC = () => {
  // Camera and permissions state
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const [cameraType, setCameraType] = useState(CameraType.back);
  const [flashMode, setFlashMode] = useState(FlashMode.off);
  const [isPreview, setIsPreview] = useState(false);

  // Photo management state
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<PhotoCategory>(PhotoCategory.EXTERIOR_FRONT);
  const [showGallery, setShowGallery] = useState(false);

  // Upload state
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [vehicleMetadata, setVehicleMetadata] = useState<VehicleMetadata>({});

  // Refs
  const cameraRef = useRef<Camera>(null);
  const navigation = useNavigation<CameraScreenNavigationProp>();

  // Screen dimensions
  const { width: screenWidth } = Dimensions.get('window');
  const previewSize = screenWidth / 3 - 12;

  // Request camera and media library permissions on mount
  useEffect(() => {
    (async () => {
      const { status: cameraStatus } = await Camera.requestCameraPermissionsAsync();
      const { status: mediaStatus } = await MediaLibrary.requestPermissionsAsync();
      
      setHasPermission(cameraStatus === 'granted' && mediaStatus === 'granted');
      
      if (cameraStatus !== 'granted' || mediaStatus !== 'granted') {
        Alert.alert(
          'Permissions Required',
          'Camera and photo library access are required to use this app. Please enable them in your device settings.',
          [{ text: 'OK' }]
        );
      }
    })();
  }, []);

  // Handle taking a photo
  const takePicture = async () => {
    if (cameraRef.current) {
      try {
        const photo = await cameraRef.current.takePictureAsync({
          quality: 0.8,
          skipProcessing: Platform.OS === 'android', // Skip processing on Android to avoid issues
        });

        // Process the image to reduce size
        const processedPhoto = await manipulateAsync(
          photo.uri,
          [{ resize: { width: 1200 } }],
          { compress: 0.8, format: SaveFormat.JPEG }
        );

        // Create a unique ID for the photo
        const photoId = uuid.v4().toString();

        // Save to media library
        await MediaLibrary.saveToLibraryAsync(processedPhoto.uri);

        // Add to photos array
        const newPhoto: Photo = {
          id: photoId,
          uri: processedPhoto.uri,
          category: selectedCategory,
          timestamp: new Date(),
        };

        setPhotos((prevPhotos) => [...prevPhotos, newPhoto]);
        setIsPreview(true);

        // Show success message
        Alert.alert(
          'Photo Captured',
          `${selectedCategory} photo saved successfully.`,
          [{ text: 'OK' }]
        );
      } catch (error) {
        console.error('Error taking picture:', error);
        Alert.alert('Error', 'Failed to take photo. Please try again.');
      }
    }
  };

  // Toggle camera type (front/back)
  const toggleCameraType = () => {
    setCameraType(current => (
      current === CameraType.back ? CameraType.front : CameraType.back
    ));
  };

  // Toggle flash mode
  const toggleFlashMode = () => {
    setFlashMode(current => (
      current === FlashMode.off ? FlashMode.on : FlashMode.off
    ));
  };

  // Pick images from gallery
  const pickImages = async () => {
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsMultipleSelection: true,
        quality: 0.8,
        aspect: [4, 3],
      });

      if (!result.canceled && result.assets.length > 0) {
        // Process each selected image
        const newPhotos: Photo[] = await Promise.all(
          result.assets.map(async (asset) => {
            // Process the image to reduce size
            const processedPhoto = await manipulateAsync(
              asset.uri,
              [{ resize: { width: 1200 } }],
              { compress: 0.8, format: SaveFormat.JPEG }
            );

            return {
              id: uuid.v4().toString(),
              uri: processedPhoto.uri,
              category: selectedCategory,
              timestamp: new Date(),
            };
          })
        );

        setPhotos((prevPhotos) => [...prevPhotos, ...newPhotos]);
        setShowGallery(false);
        
        Alert.alert(
          'Photos Added',
          `${newPhotos.length} photos added as ${selectedCategory}.`,
          [{ text: 'OK' }]
        );
      }
    } catch (error) {
      console.error('Error picking images:', error);
      Alert.alert('Error', 'Failed to pick images. Please try again.');
    }
  };

  // Remove a photo
  const removePhoto = (photoId: string) => {
    Alert.alert(
      'Remove Photo',
      'Are you sure you want to remove this photo?',
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Remove', 
          style: 'destructive',
          onPress: () => {
            setPhotos((prevPhotos) => prevPhotos.filter(photo => photo.id !== photoId));
          }
        },
      ]
    );
  };

  // Change photo category
  const changePhotoCategory = (photoId: string, newCategory: PhotoCategory) => {
    setPhotos((prevPhotos) => 
      prevPhotos.map(photo => 
        photo.id === photoId 
          ? { ...photo, category: newCategory } 
          : photo
      )
    );
  };

  // Upload photos to server
  const uploadPhotos = async () => {
    // Validate we have at least one photo
    if (photos.length === 0) {
      Alert.alert('Error', 'Please take at least one photo before uploading.');
      return;
    }

    // Confirm upload
    Alert.alert(
      'Upload Photos',
      `Upload ${photos.length} photos for analysis?`,
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Upload', 
          onPress: async () => {
            try {
              setUploading(true);
              setUploadProgress(0);

              // Prepare files for upload
              const files = await Promise.all(
                photos.map(async (photo, index) => {
                  // Get file info
                  const fileInfo = await FileSystem.getInfoAsync(photo.uri);
                  
                  // Create file name with category
                  const fileName = `${index + 1}_${photo.category.replace(/\s+/g, '_').toLowerCase()}_${Date.now()}.jpg`;
                  
                  return {
                    uri: photo.uri,
                    name: fileName,
                    type: 'image/jpeg',
                  };
                })
              );

              // Create metadata object
              const metadata: VehicleMetadata = {
                ...vehicleMetadata,
              };

              // Upload to server
              const response = await apiClient.uploadFiles(
                API_CONFIG.VEHICLES.UPLOAD,
                files,
                metadata,
                (progress) => {
                  setUploadProgress(progress);
                }
              );

              // Handle successful upload
              if (response.success) {
                const { vehicle_id, task_id } = response.data;
                
                // Navigate to results screen
                navigation.navigate('AnalysisResults', { 
                  vehicleId: vehicle_id,
                  taskId: task_id,
                });
                
                // Reset state for next use
                setPhotos([]);
                setUploadProgress(0);
              } else {
                throw new Error('Upload failed');
              }
            } catch (error) {
              console.error('Error uploading photos:', error);
              Alert.alert(
                'Upload Failed',
                'Failed to upload photos. Please check your connection and try again.',
                [{ text: 'OK' }]
              );
            } finally {
              setUploading(false);
            }
          }
        },
      ]
    );
  };

  // Navigate to vehicle form to add metadata
  const goToVehicleForm = () => {
    if (photos.length === 0) {
      Alert.alert('Error', 'Please take at least one photo before proceeding.');
      return;
    }
    
    navigation.navigate('VehicleForm', { photos });
  };

  // Render loading/permission screen
  if (hasPermission === null) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" color="#0066CC" />
        <Text style={styles.text}>Requesting camera permissions...</Text>
      </View>
    );
  }

  // Render permission denied screen
  if (hasPermission === false) {
    return (
      <View style={styles.container}>
        <MaterialIcons name="no-photography" size={64} color="#FF3B30" />
        <Text style={styles.title}>Camera Access Denied</Text>
        <Text style={styles.text}>
          Camera and photo library access are required to use this app.
          Please enable them in your device settings.
        </Text>
        <TouchableOpacity 
          style={styles.button}
          onPress={() => navigation.goBack()}
        >
          <Text style={styles.buttonText}>Go Back</Text>
        </TouchableOpacity>
      </View>
    );
  }

  // Render main camera screen
  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />
      
      {/* Camera View */}
      {!showGallery && (
        <View style={styles.cameraContainer}>
          <Camera
            ref={cameraRef}
            style={styles.camera}
            type={cameraType}
            flashMode={flashMode}
            ratio="4:3"
          >
            <View style={styles.cameraOverlay}>
              {/* Category indicator */}
              <View style={styles.categoryBadge}>
                <Text style={styles.categoryText}>{selectedCategory}</Text>
              </View>
              
              {/* Camera controls */}
              <View style={styles.cameraControls}>
                <TouchableOpacity 
                  style={styles.controlButton}
                  onPress={toggleFlashMode}
                >
                  <Ionicons 
                    name={flashMode === FlashMode.on ? "flash" : "flash-off"} 
                    size={28} 
                    color="white" 
                  />
                </TouchableOpacity>
                
                <TouchableOpacity 
                  style={styles.captureButton}
                  onPress={takePicture}
                  disabled={uploading}
                >
                  <View style={styles.captureButtonInner} />
                </TouchableOpacity>
                
                <TouchableOpacity 
                  style={styles.controlButton}
                  onPress={toggleCameraType}
                >
                  <Ionicons name="camera-reverse" size={28} color="white" />
                </TouchableOpacity>
              </View>
            </View>
          </Camera>
        </View>
      )}
      
      {/* Category selector */}
      <View style={styles.categorySelector}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          {Object.values(PhotoCategory).map((category) => (
            <TouchableOpacity
              key={category}
              style={[
                styles.categoryButton,
                selectedCategory === category && styles.categoryButtonSelected,
              ]}
              onPress={() => setSelectedCategory(category)}
            >
              <Text 
                style={[
                  styles.categoryButtonText,
                  selectedCategory === category && styles.categoryButtonTextSelected,
                ]}
              >
                {category}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>
      
      {/* Photo gallery / preview */}
      <View style={styles.galleryContainer}>
        <View style={styles.galleryHeader}>
          <Text style={styles.galleryTitle}>
            Photos ({photos.length})
          </Text>
          <TouchableOpacity 
            style={styles.galleryButton}
            onPress={() => setShowGallery(!showGallery)}
          >
            <Text style={styles.galleryButtonText}>
              {showGallery ? "Show Camera" : "Pick from Gallery"}
            </Text>
            <Ionicons 
              name={showGallery ? "camera" : "images"} 
              size={20} 
              color="#0066CC" 
            />
          </TouchableOpacity>
        </View>
        
        {showGallery ? (
          <View style={styles.galleryPickerContainer}>
            <TouchableOpacity 
              style={styles.galleryPickerButton}
              onPress={pickImages}
            >
              <Ionicons name="images" size={48} color="#0066CC" />
              <Text style={styles.galleryPickerText}>
                Select Photos from Gallery
              </Text>
            </TouchableOpacity>
          </View>
        ) : (
          <ScrollView 
            horizontal 
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.photoPreviewContainer}
          >
            {photos.length === 0 ? (
              <View style={styles.emptyPhotosContainer}>
                <Ionicons name="images-outline" size={32} color="#999" />
                <Text style={styles.emptyPhotosText}>
                  No photos yet. Take a photo or select from gallery.
                </Text>
              </View>
            ) : (
              photos.map((photo) => (
                <View key={photo.id} style={styles.photoPreview}>
                  <Image 
                    source={{ uri: photo.uri }} 
                    style={[styles.previewImage, { width: previewSize, height: previewSize }]} 
                  />
                  <View style={styles.previewOverlay}>
                    <TouchableOpacity 
                      style={styles.removePhotoButton}
                      onPress={() => removePhoto(photo.id)}
                    >
                      <Ionicons name="close-circle" size={24} color="#FF3B30" />
                    </TouchableOpacity>
                    <Text style={styles.previewCategory}>
                      {photo.category}
                    </Text>
                  </View>
                </View>
              ))
            )}
          </ScrollView>
        )}
      </View>
      
      {/* Action buttons */}
      <View style={styles.actionContainer}>
        {uploading ? (
          <View style={styles.uploadingContainer}>
            <ActivityIndicator size="large" color="#0066CC" />
            <Text style={styles.uploadingText}>
              Uploading... {uploadProgress}%
            </Text>
            <View style={styles.progressBar}>
              <View 
                style={[
                  styles.progressFill,
                  { width: `${uploadProgress}%` }
                ]} 
              />
            </View>
          </View>
        ) : (
          <>
            <TouchableOpacity 
              style={[styles.actionButton, styles.secondaryButton]}
              onPress={goToVehicleForm}
              disabled={photos.length === 0}
            >
              <Ionicons name="car" size={20} color="#0066CC" />
              <Text style={styles.secondaryButtonText}>Add Vehicle Info</Text>
            </TouchableOpacity>
            
            <TouchableOpacity 
              style={[styles.actionButton, styles.primaryButton]}
              onPress={uploadPhotos}
              disabled={photos.length === 0}
            >
              <Ionicons name="cloud-upload" size={20} color="white" />
              <Text style={styles.primaryButtonText}>Upload for Analysis</Text>
            </TouchableOpacity>
          </>
        )}
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F2F2F7',
  },
  cameraContainer: {
    flex: 1,
    overflow: 'hidden',
    borderRadius: 8,
    margin: 8,
  },
  camera: {
    flex: 1,
    justifyContent: 'flex-end',
  },
  cameraOverlay: {
    flex: 1,
    backgroundColor: 'transparent',
    justifyContent: 'space-between',
    padding: 16,
  },
  cameraControls: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    width: '100%',
    paddingHorizontal: 20,
    paddingBottom: 20,
  },
  controlButton: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: 'rgba(0,0,0,0.3)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  captureButton: {
    width: 70,
    height: 70,
    borderRadius: 35,
    backgroundColor: 'rgba(255,255,255,0.3)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: 'white',
  },
  captureButtonInner: {
    width: 54,
    height: 54,
    borderRadius: 27,
    backgroundColor: 'white',
  },
  categoryBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: 'rgba(0,0,0,0.6)',
    borderRadius: 16,
    alignSelf: 'flex-start',
    marginTop: 16,
  },
  categoryText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 14,
  },
  categorySelector: {
    height: 50,
    backgroundColor: 'white',
    borderRadius: 8,
    margin: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  categoryButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    margin: 8,
    borderRadius: 16,
    backgroundColor: '#F2F2F7',
  },
  categoryButtonSelected: {
    backgroundColor: '#0066CC',
  },
  categoryButtonText: {
    fontSize: 14,
    color: '#333',
  },
  categoryButtonTextSelected: {
    color: 'white',
    fontWeight: 'bold',
  },
  galleryContainer: {
    height: 180,
    backgroundColor: 'white',
    borderRadius: 8,
    margin: 8,
    padding: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  galleryHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  galleryTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  galleryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 8,
  },
  galleryButtonText: {
    color: '#0066CC',
    marginRight: 4,
  },
  galleryPickerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  galleryPickerButton: {
    justifyContent: 'center',
    alignItems: 'center',
    padding: 16,
  },
  galleryPickerText: {
    color: '#0066CC',
    marginTop: 8,
    fontSize: 16,
  },
  photoPreviewContainer: {
    paddingVertical: 8,
  },
  photoPreview: {
    marginRight: 8,
    borderRadius: 8,
    overflow: 'hidden',
    position: 'relative',
  },
  previewImage: {
    borderRadius: 8,
  },
  previewOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.2)',
    borderRadius: 8,
    justifyContent: 'space-between',
    padding: 4,
  },
  removePhotoButton: {
    alignSelf: 'flex-end',
  },
  previewCategory: {
    color: 'white',
    fontSize: 10,
    fontWeight: 'bold',
    padding: 4,
    backgroundColor: 'rgba(0,0,0,0.5)',
    borderRadius: 4,
  },
  emptyPhotosContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 16,
  },
  emptyPhotosText: {
    color: '#999',
    textAlign: 'center',
    marginTop: 8,
  },
  actionContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: 8,
    marginBottom: Platform.OS === 'ios' ? 20 : 8,
  },
  actionButton: {
    flex: 1,
    height: 50,
    borderRadius: 25,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginHorizontal: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.2,
    shadowRadius: 2,
    elevation: 3,
  },
  primaryButton: {
    backgroundColor: '#0066CC',
  },
  secondaryButton: {
    backgroundColor: 'white',
    borderWidth: 1,
    borderColor: '#0066CC',
  },
  primaryButtonText: {
    color: 'white',
    fontWeight: 'bold',
    marginLeft: 8,
  },
  secondaryButtonText: {
    color: '#0066CC',
    fontWeight: 'bold',
    marginLeft: 8,
  },
  uploadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 16,
  },
  uploadingText: {
    color: '#0066CC',
    fontWeight: 'bold',
    marginTop: 8,
    marginBottom: 8,
  },
  progressBar: {
    width: '100%',
    height: 8,
    backgroundColor: '#E5E5EA',
    borderRadius: 4,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#0066CC',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginVertical: 16,
  },
  text: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    marginHorizontal: 24,
    marginVertical: 8,
  },
  button: {
    marginTop: 24,
    paddingVertical: 12,
    paddingHorizontal: 24,
    backgroundColor: '#0066CC',
    borderRadius: 24,
  },
  buttonText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 16,
  },
});

export default CameraScreen;
