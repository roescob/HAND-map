#Compiled by Roberto Javier Escobar Mou.
import processing
from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (
QgsProcessing, 
QgsProcessingAlgorithm, 
QgsProcessingParameterRasterLayer, 
QgsProcessingParameterNumber, 
QgsProcessingParameterRasterDestination, 
QgsRasterLayer)
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
class ExAlgo(QgsProcessingAlgorithm):

    raster_layer = 'INPUT'
    stream_threshold = 'stream_threshold'
    OUTPUT = 'OUTPUT'
 
    def __init__(self):
        super().__init__()
    def name(self):
        return "pcrasterhand"
    def tr(self, text):
        return QCoreApplication.translate("exalgo", text)
    def displayName(self):
        return self.tr("HAND map derived from PCRaster plugin")
    def shortHelpString(self):
        return self.tr("Implements PCRaster tools plugin to generate a HAND map. \
        As explained by Hans van der Kwast")
    #def helpUrl(self):
    #    return "https://qgis.org"
    def createInstance(self):
        return type(self)()
    def initAlgorithm(self, config=None):

        self.addParameter(QgsProcessingParameterRasterLayer(
            self.raster_layer,
            self.tr("Input Digital Elevation Model"),
            [QgsProcessing.TypeRaster]))
            
        #STREAM THRESHOLD
        self.addParameter(QgsProcessingParameterNumber (
            self.stream_threshold,
            self.tr("Stream threshold"), defaultValue=3000
            ))
            
        self.addParameter(QgsProcessingParameterRasterDestination(
            self.OUTPUT,
            self.tr("Output Directory"),
            ))
 
    def processAlgorithm(self, parameters, context, feedback):
        raster_a = self.parameterAsRasterLayer(parameters, self.raster_layer, context)
        stream_threshold_a = self.parameterAsString(parameters, self.stream_threshold, context)
        output_path_raster_a = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        #STEPS
        #1.Convert to workable format
        processing.run("pcraster:converttopcrasterformat",\
            {'INPUT':raster_a,\
            'INPUT2':3,\
                'OUTPUT':'pcraster_temp'})
        #2. Generate flow direction
        processing.run("pcraster:lddcreate", \
            {'INPUT':'pcraster_temp',\
            'INPUT0':0,'INPUT1':0,'INPUT2':9999999,'INPUT4':9999999,'INPUT3':9999999,'INPUT5':9999999,\
                'OUTPUT':'lddcreate_temp'})
        #3. Create raster with scalar value 1.
        processing.run("pcraster:spatial", \
            {'INPUT':1,'INPUT1':3,\
            'INPUT2':'lddcreate_temp',\
                'OUTPUT':'scalar_temp'})
        #4. Generate accumulated material flowing downstream
        processing.run("pcraster:accuflux", \
            {'INPUT':'lddcreate_temp',\
            'INPUT2':'scalar_temp',\
                'OUTPUT':'accuflux_temp'})
        #5. Extract accumulated material
        processing.run("pcraster:spatial", \
            {'INPUT':stream_threshold_a,'INPUT1':3,\
            'INPUT2':'accuflux_temp',\
                'OUTPUT':'spatial_temp'})
        #6. Clean
        processing.run("pcraster:comparisonoperators", \
            {'INPUT':'accuflux_temp',\
            'INPUT1':1,'INPUT2':'spatial_temp',\
                'OUTPUT':'comparison_operator_temp'})
        #7. Clean
        processing.run("pcraster:uniqueid", \
            {'INPUT':'comparison_operator_temp',\
                'OUTPUT':'uniqueid_temp'})
        #8. Convert from scalar to nominal
        processing.run("pcraster:convertdatatype", \
            {'INPUT':'uniqueid_temp',\
            'INPUT1':1,\
                'OUTPUT':'convertlayerdatatype_temp'})
        #9. Generate sub-catchments
        processing.run("pcraster:subcatchment", \
            {'INPUT1':'lddcreate_temp',\
            'INPUT2':'convertlayerdatatype_temp',\
                'OUTPUT':'subcatchment_temp'})
        #10. Areaminimum
        processing.run("pcraster:areaminimum", \
            {'INPUT':'subcatchment_temp',\
            'INPUT2':'pcraster_temp',\
                'OUTPUT':'areaminimum_temp'})
        #11. HAND elevation subtraction
        #RasterCalculator inputs and outputs
        areaminimum_rastercalculator_temp = QgsRasterLayer(r'areaminimum_temp')
        pcraster_rastercalculator_temp = QgsRasterLayer(r'pcraster_temp')

        #preparing layers for RasterCalculator
        entries = []
        amr = QgsRasterCalculatorEntry()
        amr.ref = 'amin@1'
        amr.raster = areaminimum_rastercalculator_temp
        amr.bandNumber = 1
        entries.append( amr )
        pcr = QgsRasterCalculatorEntry()
        pcr.ref = 'pcr@2'
        pcr.raster = pcraster_rastercalculator_temp
        pcr.bandNumber = 1
        entries.append( pcr )

        #Process calculation with input extent and resolution
        calc = QgsRasterCalculator( 'pcr@2 - amin@1',
                                    output_path_raster_a,
                                    'GTiff',
                                    pcraster_rastercalculator_temp.extent(), 
                                    pcraster_rastercalculator_temp.width(), 
                                    pcraster_rastercalculator_temp.height(), 
                                    entries )

        calc.processCalculation()
 
        results = {}
        results[self.OUTPUT] = output_path_raster_a
        return results
