import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import NetInfo from '@react-native-community/netinfo';
import { Platform } from 'react-native';
import Constants from 'expo-constants';

// API Configuration
export const API_CONFIG = {
  // Base URL - change this to your actual backend URL when deploying
  // In development we try to automatically discover the LAN IP address of the
  // machine running the Expo packager so that a *real* device (iPhone / Android)
  // can reach the backend running on the same computer.
  BASE_URL: __DEV__
    ? (() => {
        // When running in Expo the debuggerHost / hostUri usually looks like
        //   "192.168.1.42:19000" or "192.168.1.42:19000/..."
        // We only need the IP part and then append the backend port & path.
        const host =
          // Newer Expo SDKs (48+) expose hostUri in expoConfig at runtime
          (Constants.expoConfig as any)?.hostUri ??
          // Fallback for classic manifest
          (Constants.manifest as any)?.debuggerHost ??
          '';

        if (host) {
          const ip = host.split(':')[0];
          return `http://${ip}:8000/api/v1`;
        }

        // Ultimate fallback – works for Android emulator but NOT for real devices.
        // Users can still override this via env or editing the file.
        return 'http://10.0.2.2:8000/api/v1';
      })()
    : 'https://api.carauctionanalyzer.com/api/v1', // Production URL
  
  // Authentication endpoints
  AUTH: {
    LOGIN: '/auth/login',
    REGISTER: '/auth/register',
    REFRESH_TOKEN: '/auth/refresh',
    LOGOUT: '/auth/logout',
    VERIFY_EMAIL: '/auth/verify-email',
    FORGOT_PASSWORD: '/auth/forgot-password',
    RESET_PASSWORD: '/auth/reset-password',
  },
  
  // Vehicle endpoints
  VEHICLES: {
    LIST: '/vehicles',
    UPLOAD: '/vehicles',
    DETAILS: (id: string) => `/vehicles/${id}`,
    REPORT: (id: string) => `/vehicles/${id}/report`,
    DELETE: (id: string) => `/vehicles/${id}`,
    WEBSOCKET: (id: string) => `/vehicles/ws/${id}`,
  },
  
  // Market data endpoints
  MARKET: {
    PRICE: '/market/price',
    TRENDS: '/market/trends',
    SIMILAR_VEHICLES: '/market/similar-vehicles',
  },
  
  // Parts and repair endpoints
  PARTS: {
    ESTIMATE: '/parts/estimate',
    SEARCH: '/parts/search',
    AVAILABILITY: '/parts/availability',
  },
  
  // User profile endpoints
  USERS: {
    PROFILE: '/users/me',
    UPDATE_PROFILE: '/users/me',
    CHANGE_PASSWORD: '/users/me/password',
  },
  
  // Health check
  HEALTH: '/health',
  
  // Request timeout in milliseconds
  TIMEOUT: 30000,
  
  // Maximum number of retry attempts
  MAX_RETRIES: 3,
};

// Token storage keys
const TOKEN_STORAGE = {
  ACCESS_TOKEN: 'car_auction_access_token',
  REFRESH_TOKEN: 'car_auction_refresh_token',
  USER_DATA: 'car_auction_user_data',
};

// API response interface
export interface ApiResponse<T = any> {
  data: T;
  message?: string;
  status: number;
  success: boolean;
}

// Error response interface
export interface ApiError {
  status: number;
  message: string;
  errors?: Record<string, string[]>;
  timestamp?: string;
}

// Create API client class
class ApiClient {
  private instance: AxiosInstance;
  private isRefreshing: boolean = false;
  private refreshSubscribers: Array<(token: string) => void> = [];

  constructor() {
    // Create axios instance
    this.instance = axios.create({
      baseURL: API_CONFIG.BASE_URL,
      timeout: API_CONFIG.TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-Client-Platform': Platform.OS,
        'X-Client-Version': Constants.expoConfig?.version || '1.0.0',
      },
    });

    // Setup request interceptor for authentication
    this.instance.interceptors.request.use(
      async (config) => {
        // Check network connectivity
        const netInfo = await NetInfo.fetch();
        if (!netInfo.isConnected) {
          throw new Error('No internet connection');
        }

        // Add auth token if available
        const token = await AsyncStorage.getItem(TOKEN_STORAGE.ACCESS_TOKEN);
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Setup response interceptor for error handling and token refresh
    this.instance.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };
        
        // Handle 401 Unauthorized error (token expired)
        if (error.response?.status === 401 && !originalRequest._retry) {
          if (this.isRefreshing) {
            // If already refreshing, wait for new token
            return new Promise((resolve) => {
              this.refreshSubscribers.push((token: string) => {
                if (originalRequest.headers) {
                  originalRequest.headers.Authorization = `Bearer ${token}`;
                }
                resolve(this.instance(originalRequest));
              });
            });
          }

          originalRequest._retry = true;
          this.isRefreshing = true;

          try {
            // Try to refresh the token
            const refreshToken = await AsyncStorage.getItem(TOKEN_STORAGE.REFRESH_TOKEN);
            if (!refreshToken) {
              // No refresh token available, user needs to login again
              await this.clearAuthData();
              throw new Error('Authentication required');
            }

            const response = await axios.post(
              `${API_CONFIG.BASE_URL}${API_CONFIG.AUTH.REFRESH_TOKEN}`,
              { refresh_token: refreshToken }
            );

            const { access_token, refresh_token } = response.data;
            
            // Save new tokens
            await AsyncStorage.setItem(TOKEN_STORAGE.ACCESS_TOKEN, access_token);
            await AsyncStorage.setItem(TOKEN_STORAGE.REFRESH_TOKEN, refresh_token);
            
            // Update authorization header
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${access_token}`;
            }
            
            // Notify all waiting requests
            this.refreshSubscribers.forEach(callback => callback(access_token));
            this.refreshSubscribers = [];
            this.isRefreshing = false;
            
            // Retry original request
            return this.instance(originalRequest);
          } catch (refreshError) {
            // Token refresh failed, clear auth data
            this.refreshSubscribers = [];
            this.isRefreshing = false;
            await this.clearAuthData();
            throw new Error('Authentication required');
          }
        }

        // Handle network errors
        if (!error.response) {
          throw new Error('Network error. Please check your connection.');
        }

        // Extract error details from response
        const errorData = error.response.data as ApiError;
        const errorMessage = errorData.message || 'An unexpected error occurred';
        
        // Create standardized error object
        const apiError: ApiError = {
          status: error.response.status,
          message: errorMessage,
          errors: errorData.errors,
          timestamp: errorData.timestamp || new Date().toISOString(),
        };

        throw apiError;
      }
    );
  }

  // Clear authentication data
  async clearAuthData(): Promise<void> {
    await AsyncStorage.multiRemove([
      TOKEN_STORAGE.ACCESS_TOKEN,
      TOKEN_STORAGE.REFRESH_TOKEN,
      TOKEN_STORAGE.USER_DATA,
    ]);
  }

  // Save authentication data
  async saveAuthData(accessToken: string, refreshToken: string, userData: any): Promise<void> {
    await AsyncStorage.multiSet([
      [TOKEN_STORAGE.ACCESS_TOKEN, accessToken],
      [TOKEN_STORAGE.REFRESH_TOKEN, refreshToken],
      [TOKEN_STORAGE.USER_DATA, JSON.stringify(userData)],
    ]);
  }

  // Check if user is authenticated
  async isAuthenticated(): Promise<boolean> {
    const token = await AsyncStorage.getItem(TOKEN_STORAGE.ACCESS_TOKEN);
    return !!token;
  }

  // Get user data
  async getUserData<T = any>(): Promise<T | null> {
    const userData = await AsyncStorage.getItem(TOKEN_STORAGE.USER_DATA);
    return userData ? JSON.parse(userData) : null;
  }

  // Generic request method
  async request<T = any>(config: AxiosRequestConfig): Promise<ApiResponse<T>> {
    try {
      const response: AxiosResponse = await this.instance(config);
      return {
        data: response.data,
        status: response.status,
        success: true,
      };
    } catch (error) {
      if ((error as ApiError).status) {
        throw error;
      }
      throw {
        status: 500,
        message: (error as Error).message || 'Unknown error occurred',
        success: false,
      };
    }
  }

  // GET request
  async get<T = any>(url: string, params?: any): Promise<ApiResponse<T>> {
    return this.request<T>({ method: 'GET', url, params });
  }

  // POST request
  async post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    return this.request<T>({ method: 'POST', url, data, ...config });
  }

  // PUT request
  async put<T = any>(url: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>({ method: 'PUT', url, data });
  }

  // PATCH request
  async patch<T = any>(url: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>({ method: 'PATCH', url, data });
  }

  // DELETE request
  async delete<T = any>(url: string): Promise<ApiResponse<T>> {
    return this.request<T>({ method: 'DELETE', url });
  }

  // Upload files with form data
  async uploadFiles<T = any>(
    url: string, 
    files: Array<{ uri: string; name: string; type: string }>,
    data?: Record<string, any>,
    onProgress?: (progress: number) => void
  ): Promise<ApiResponse<T>> {
    const formData = new FormData();
    
    // Append files to form data
    files.forEach((file, index) => {
      formData.append('files', {
        uri: file.uri,
        name: file.name,
        type: file.type,
      } as any);
    });
    
    // Append additional data as JSON
    if (data) {
      formData.append('data', JSON.stringify(data));
    }
    
    return this.request<T>({
      method: 'POST',
      url,
      data: formData,
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: onProgress 
        ? (progressEvent) => {
            const percentCompleted = Math.round(
              (progressEvent.loaded * 100) / (progressEvent.total || 100)
            );
            onProgress(percentCompleted);
          }
        : undefined,
    });
  }

  // Health check
  async checkHealth(): Promise<boolean> {
    try {
      const response = await this.get(API_CONFIG.HEALTH);
      return response.status === 200;
    } catch (error) {
      return false;
    }
  }
}

// Create and export API client instance
export const apiClient = new ApiClient();

// Export token storage for direct access if needed
export { TOKEN_STORAGE };
