import React, { useEffect, useState, useRef } from 'react';
import { StatusBar } from 'expo-status-bar';
import { StyleSheet, View, FlatList, Dimensions, ActivityIndicator, Text, TouchableOpacity } from 'react-native';
import { Video } from 'expo-av';
import { Ionicons } from '@expo/vector-icons';

const { height: SCREEN_HEIGHT } = Dimensions.get('window');

export default function App() {
  const [reels, setReels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const videoRefs = useRef([]);
  const [isPlaying, setIsPlaying] = useState(true);

  useEffect(() => {
    let isMounted = true;
    fetch('https://dev.cloudtix.in/reels')
      .then((res) => {
        if (!res.ok) throw new Error('Failed to fetch reels');
        return res.json();
      })
      .then((data) => {
        if (isMounted) {
          setReels(data);
        }
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
    // Polling for new reels every 30 seconds
    const interval = setInterval(() => {
      fetch('https://dev.cloudtix.in/reels')
        .then((res) => {
          if (!res.ok) throw new Error('Failed to fetch reels');
          return res.json();
        })
        .then((data) => {
          if (isMounted) {
            setReels((prevReels) => {
              // Merge new reels that are not already present
              const existingIds = new Set(prevReels.map(r => r._id));
              const newReels = data.filter(r => !existingIds.has(r._id));
              return [...prevReels, ...newReels];
            });
          }
        })
        .catch(() => {});
    }, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const onViewableItemsChanged = useRef(({ viewableItems }) => {
    if (viewableItems.length > 0) {
      setCurrentIndex(viewableItems[0].index);
    }
  }).current;

  const viewabilityConfig = useRef({
    itemVisiblePercentThreshold: 80,
  }).current;

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centered}>
        <Text>Error: {error}</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={reels}
        keyExtractor={(item, idx) => idx.toString()}
        pagingEnabled
        showsVerticalScrollIndicator={false}
        renderItem={({ item, index }) => (
          <View style={{ height: SCREEN_HEIGHT }}>
            <TouchableOpacity
              activeOpacity={1}
              style={{ flex: 1 }}
              onPress={() => setIsPlaying((prev) => !prev)}
            >
              <Video
                ref={ref => (videoRefs.current[index] = ref)}
                source={{ uri: item.url }}
                style={styles.video}
                resizeMode="cover"
                shouldPlay={currentIndex === index && isPlaying}
                isLooping
                volume={1.0}
              />
              {/* Instagram-style overlays */}
              <View style={styles.overlayContainer} pointerEvents="box-none">
                {/* Bottom left: username and caption */}
                <View style={styles.bottomLeftOverlay}>
                  <Text style={styles.username}>@username</Text>
                  <Text style={styles.caption}>This is a sample caption for the reel.</Text>
                </View>
                {/* Bottom right: action buttons */}
                <View style={styles.bottomRightOverlay}>
                  <TouchableOpacity style={styles.actionButton}>
                    <Ionicons name="heart-outline" size={32} color="white" />
                    <Text style={styles.actionLabel}>Like</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={styles.actionButton}>
                    <Ionicons name="chatbubble-outline" size={32} color="white" />
                    <Text style={styles.actionLabel}>Comment</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={styles.actionButton}>
                    <Ionicons name="share-social-outline" size={32} color="white" />
                    <Text style={styles.actionLabel}>Share</Text>
                  </TouchableOpacity>
                </View>
                {/* Center: play/pause icon */}
                {currentIndex === index && (
                  <View style={styles.playPauseButton} pointerEvents="none">
                    <Ionicons
                      name={isPlaying ? 'pause' : 'play'}
                      size={60}
                      color="white"
                    />
                  </View>
                )}
              </View>
            </TouchableOpacity>
          </View>
        )}
        onViewableItemsChanged={onViewableItemsChanged}
        viewabilityConfig={viewabilityConfig}
        snapToInterval={SCREEN_HEIGHT}
        decelerationRate="fast"
      />
      <StatusBar style="light" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  video: {
    width: '100%',
    height: '100%',
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#000',
  },
  playPauseButton: {
    position: 'absolute',
    top: '45%',
    left: '45%',
    backgroundColor: 'rgba(0,0,0,0.3)',
    opacity: 0.5,
    borderRadius: 40,
    padding: 10,
    zIndex: 10,
  },
  overlayContainer: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'flex-end',
    flexDirection: 'row',
    zIndex: 20,
  },
  bottomLeftOverlay: {
    position: 'absolute',
    left: 16,
    bottom: 32,
    maxWidth: '60%',
  },
  username: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 18,
    marginBottom: 4,
  },
  caption: {
    color: 'white',
    fontSize: 15,
  },
  bottomRightOverlay: {
    position: 'absolute',
    right: 16,
    bottom: 32,
    alignItems: 'center',
  },
  actionButton: {
    alignItems: 'center',
    marginBottom: 24,
  },
  actionLabel: {
    color: 'white',
    fontSize: 12,
    marginTop: 2,
  },
});
