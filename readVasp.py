#!/usr/bin/env python


import datetime, re, sys, traceback, os.path
import xml.etree.cElementTree as etree
import numpy as np


buglev = 0  # xxx make a parm

#====================================================================

class ResClass:
  def __str__(self):
    keys = self.__dict__.keys()
    keys.sort()
    msg = ''
    for key in keys:
      val = self.__dict__[key]
      stg = str( val)
      if stg.find('\n') >= 0: sep = '\n'
      else: sep = ' '
      msg += '  %s:  type: %s  val:%s%s\n' % (key, type(val), sep, val,)
    return msg

#====================================================================


def badparms( msg):
  print '\nError: %s' % (msg,)
  print 'Parms:'
  print '  -buglev    <int>      debug level'
  print '  -inType    <string>   pylada / xml'
  print '  -inDir     <string>   dir containing input OUTCAR or vasprun.xml'
  print '  -maxLev    <int>      max levels to print for xml'
  print ''
  print 'Examples:'
  print './readVasp.py -buglev 5   -inType xml   -inDir tda/testlada.2013.04.15.fe.len.3.20/icsd_044729/icsd_044729.cif/hs-anti-ferro-0/relax_cellshape/0   -maxLev 0'
  sys.exit(1)

#====================================================================


def main():
  buglev = 0
  inType = None
  inDir = None
  maxLev = None

  if len(sys.argv) % 2 != 1:
    badparms('Parms must be key/value pairs')
  for iarg in range( 1, len(sys.argv), 2):
    key = sys.argv[iarg]
    val = sys.argv[iarg+1]
    if key == '-buglev': buglev = int( val)
    elif key == '-inType': inType = val
    elif key == '-inDir': inDir = val
    elif key == '-maxLev': maxLev = int( val)
    else: badparms('unknown key: "%s"' % (key,))

  if buglev == None: badparms('parm not specified: -buglev')
  if inType == None: badparms('parm not specified: -inType')
  if inDir == None: badparms('parm not specified: -inDir')
  if maxLev == None: badparms('parm not specified: -maxLev')

  ##np.set_printoptions( threshold=10000)

  resObj = parseDir( buglev, inType, inDir, maxLev)

  print 'main: resObj:\n%s' % (resObj,)


#====================================================================


# Returns ResClass instance.

def parseDir(
  buglev,
  inType,
  inDir,
  maxLev):

  if not os.path.isdir(inDir):
    throwerr('inDir is not a dir: "%s"' % (inDir,))

  # Extract the ICSD number from realPath '.../icsd_dddddd/...'
  realPath = os.path.realpath( inDir)
  mat = re.match('^.*/icsd_(\d{6})/.*$', realPath)
  if mat == None:
    throwerr('no icsd id found in inDir name: "%s"' % (realPath,))
  icsdNum = int( mat.group(1))

  # Extract magnetic moment type from realPath
  magType = None
  magNum = 0
  pairs = [['hs-ferro',      'hsf'],
           ['hs-anti-ferro', 'hsaf'],
           ['ls-ferro',      'lsf'],
           ['ls-anti-ferro', 'lsaf'],
           ['non-magnetic',  'nm']]
  for (tname,tcode) in pairs:
    ix = realPath.find( tname)
    if ix >= 0:
      magType = tcode
      if tcode in ['hsaf', 'lsaf']:
        rest = realPath[(ix+len(tname)):]
        mat = re.match('^-(\d+).*$', rest)
        if mat == None:
          throwerr('no magNum found in realPath: "%s"' % (realPath,))
        magNum = int( mat.group(1))
      break
  if magType == None:
    throwerr('no magType found in realPath: "%s"' % (realPath,))

  # Extract relaxType from realPath

  # If realPath contains 'relax_cellshape', set relaxType = 'rc'
  # and relaxNum = the number of the subfolder.  Similarly for 'relax_ions'.
  relaxType = 'std'
  relaxNum = 0
  pairs = [['relax_cellshape', 'rc'],
           ['relax_ions',      'ri']]
  for (tname,tcode) in pairs:
    ix = realPath.find( tname)
    if ix >= 0:
      relaxType = tcode
      rest = realPath[(ix+len(tname)):]
      mat = re.match('^/(\d+).*$', rest)
      if mat == None:
        throwerr('no subfolder found in realPath: "%s"' % (realPath,))
      relaxNum = int( mat.group(1))
      break

  # Get statistics on files in this dir.
  fileNames = os.listdir( inDir)
  fileNames.sort()
  fileSizes = []
  for fname in fileNames:
    path = inDir + '/' + fname
    if os.path.isfile(path):
      fstat = os.stat( path)
      fileSizes.append( fstat.st_size)



  resObj = ResClass()
  resObj.realPath = realPath
  resObj.icsdNum = icsdNum
  resObj.magType = magType
  resObj.magNum = magNum
  resObj.relaxType = relaxType
  resObj.relaxNum = relaxNum
  resObj.excMsg = None
  resObj.excTrace = None
  resObj.fileNames = fileNames
  resObj.fileSizes = fileSizes

  try:
    if inType == 'pylada':
      inFile = inDir + '/OUTCAR'
      if not os.path.isfile(inFile):
        throwerr('inFile is not a file: "%s"' % (inFile,))
      parsePylada( buglev, inFile, resObj)
    elif inType == 'xml':
      inFile = inDir + '/vasprun.xml'
      if not os.path.isfile(inFile):
        throwerr('inFile is not a file: "%s"' % (inFile,))
      parseXml( buglev, inFile, maxLev, resObj)
    else: throwerr('unknown inType: %s' % (inType,))
  except Exception, exc:
    resObj.excTrace = traceback.format_exc( limit=None)
    resObj.excMsg = repr(exc)
    print 'readVasp.py.  caught exc: %s' % (resObj.excMsg,)
    print '  inType:   "%s"' % (inType,)
    print '  inDir:    "%s"' % (inDir,)
    print '  realPath: "%s"' % (realPath,)
    print '  icsdNum:  %d'   % (icsdNum,)
    print '===== traceback start ====='
    print resObj.excTrace
    print '===== traceback end ====='

  return resObj

#====================================================================

def parsePylada( buglev, inFile, resObj):

  import pylada.vasp

  ex = pylada.vasp.Extract( inFile)
  if not ex.success: throwerr('file %s is not complete' % (inFile,))

  #===== program, version, date etc =====
  resObj.runDate      = ex.datetime

  # iterTimes are pairs: [cpuTime, realTime]
  resObj.iterCpuTimes   = [pair[0] for pair in ex.iterTimes]
  resObj.iterRealTimes  = [pair[1] for pair in ex.iterTimes]
  resObj.iterTotalTime = np.sum( resObj.iterRealTimes)

  #===== incar parameters =====
  # Use float() to get rid of Quantities units
  resObj.algo         = ex.algo
  resObj.ediff        = float( ex.ediff)
  resObj.encut        = float( ex.encut)
  resObj.ibrion       = ex.ibrion
  resObj.isif         = ex.isif
  resObj.systemName   = ex.system
  #===== general parameters =====
  #===== electronic parameters =====
  resObj.ialgo        = ex.ialgo
  resObj.numBand      = ex.nbands
  resObj.numElectron  = ex.nelect
  resObj.icharg       = ex.icharg
  resObj.numSpin      = ex.ispin


  #===== atom info =====
  resObj.typeNames    = np.array( ex.species, dtype=str)
  resObj.typeNums     = np.array( ex.stoichiometry, dtype=int)
  resObj.typeValences = np.array( ex.ionic_charges, dtype=float)

  # totalValence = sum( count[i] * valence[i])
  # PyLada calls this valence.
  resObj.totalValence = np.dot( resObj.typeNums, resObj.typeValences)
  if buglev >= 5: print 'totalValence: %g' % (resObj.totalValence,)
  if resObj.numElectron != resObj.totalValence:
    # xxx should this be an error?
    print('%g == numElectron != totalValence == %g' \
      % (resObj.numElectron, resObj.totalValence,))

  struct = ex.structure
  natom = len( struct)
  resObj.atomNames = [ struct[ii].type for ii in range( natom)]

  resObj.atomMasses = None          # not available
  resObj.atomPseudos = None         # not available
  resObj.atomValences = None        # not available

  # atomPseudos: only the first title is available
  # atomMass, Valence: not available

  # partial_charges and magnetization are not available in xml
  # resObj.partialChargeMat = ex.partial_charges
  # resObj.magnetizationMat = ex.magnetization

  #===== initial structure =====
  resObj.initialBasisMat = ex.initial_structure.cell
  resObj.initialRecipBasisMat = np.linalg.inv( resObj.initialBasisMat)

  struct = ex.initial_structure
  natom = len( struct)
  cartPos = natom * [None]
  for ii in range( natom):
    cartPos[ii] = struct[ii].pos

  resObj.initialCartesianPosMat = np.array( cartPos)

  resObj.initialDirectPosMat = np.dot(
    resObj.initialCartesianPosMat, resObj.initialRecipBasisMat)

  #===== final structure =====
  resObj.finalBasisMat = ex.structure.cell

  # xxx: not quite true:
  resObj.finalRecipBasisMat = np.linalg.inv( resObj.finalBasisMat)

  struct = ex.structure
  natom = len( struct)
  cartPos = natom * [None]
  for ii in range( natom):
    cartPos[ii] = struct[ii].pos

  resObj.finalCartesianPosMat = np.array( cartPos)

  resObj.finalDirectPosMat = np.dot(
    resObj.finalCartesianPosMat, resObj.finalRecipBasisMat)

  #===== kpoints =====
  resObj.kpointRecipSpaceCartCoords = ex.kpoints    # transform
  resObj.numKpoint = resObj.kpointRecipSpaceCartCoords.shape[0]
  resObj.kpointWeights = None          # xxx not available
  resObj.kpointRecipSpaceFracCoords = \
    np.dot( resObj.kpointRecipSpaceCartCoords, resObj.initialBasisMat)
  if buglev >= 5:
    print 'numKpoint: %g' % (resObj.numKpoint,)
    print 'kpointRecipSpaceFracCoords:\n%s' \
      % (repr(resObj.kpointRecipSpaceFracCoords),)
    print 'kpointRecipSpaceCartCoords:\n%s' \
      % (repr(resObj.kpointRecipSpaceCartCoords),)
  #===== final volume and density =====
  resObj.finalVolumeVasp = float( ex.volume)   # Angstrom^3
  resObj.density = float( ex.density)          # g/cm3
  #===== last calc forces =====
  resObj.finalForceMat = np.array( ex.forces)
  resObj.finalStressMat = np.array( ex.stress)
  resObj.finalPressure = float( ex.pressure)
  #===== eigenvalues and occupancies =====
  resObj.eigenMat = np.array( ex.eigenvalues)
  # Caution: for non-magnetic, OUTCAR occMat = 2 while vasprun.xml = 1.
  # For magnetic, OUTCAR and vasprun.xml both have 1.
  resObj.occMat = np.array( ex.occupations)
  #===== misc junk =====
  #===== energy, efermi0 =====
  resObj.finalEnergyWithout = float( ex.total_energy)
  resObj.efermi0      = float( ex.fermi0K)
  #===== cbMin, vbMax, bandgap =====
  resObj.cbMin        = float( ex.cbm)
  resObj.vbMax        = float( ex.vbm)
  resObj.bandgap      = resObj.cbMin - resObj.vbMax
  if buglev >= 5:
    print 'cbMin: %g' % (resObj.cbMin,)
    print 'vbMax: %g' % (resObj.vbMax,)
    print 'bandgap:  %g' % (resObj.bandgap,)

  resObj.cbms         = None                  # not available
  resObj.vbms         = None                  # not available
  resObj.cbmKpis      = None                  # not available
  resObj.vbmKpis      = None                  # not available
  resObj.bandgapa     = None                  # not available
  resObj.bandgaps     = None                  # not available

  return

# xxx to do:
#   energy               == totalEnergy
#   energy_sigma0        totalEnergySigma0
#   fermi0K              fermi0
#   fermi_energy         fermiEnergy
#   total_energy         totalEnergy
# array(-13.916343) * eV

#====================================================================

def parseXml( buglev, inXml, maxLev, resObj):

  tree = etree.parse( inXml)
  root = tree.getroot()
  if buglev >= 1: printNode( root, 0, maxLev)      # node, curLev, maxLev

  if buglev >= 5: print '\n===== program, version, date etc =====\n'

  # xxx program, version, subversion, etc

  # PyLada: vasp/extract/base.py: datetime()
  # OUTCAR: use the 1 occurance of:
  #   executed on             LinuxIFC date 2013.03.11  09:32:24
  dtStg = getString( root, 'generator/i[@name=\'date\']')
  tmStg = getString( root, 'generator/i[@name=\'time\']')
  dateFmtIn = '%Y %m %d %H:%M:%S'
  dateFmtOut = '%Y-%m-%d %H:%M:%S'
  resObj.runDate = datetime.datetime.strptime(
    '%s %s' % (dtStg, tmStg), dateFmtIn)
  if buglev >= 5: print 'runDate: %s' % (resObj.runDate.strftime( dateFmtOut),)


  # iterTimes
  # Each node is has cpuTime, wallTime:
  #       <time name='totalsc'>22.49 24.43</time>
  nodes = root.findall('calculation/time[@name=\'totalsc\']')
  iterCpuTimes = []
  iterRealTimes = []
  for node in nodes:
    txt = node.text
    toks = txt.split()
    if len(toks) != 2: throwerr('invalid times: %s' % (node,))
    iterCpuTimes.append( float( toks[0]))
    iterRealTimes.append( float( toks[1]))
  resObj.iterCpuTimes = iterCpuTimes
  resObj.iterRealTimes = iterRealTimes
  resObj.iterTotalTime = np.sum( iterRealTimes)
  if buglev >= 5:
    print 'iterCpuTimes: %s' % (resObj.iterCpuTimes,)
    print 'iterRealTimes: %s' % (resObj.iterRealTimes,)
    print 'iterTotalTime: %s' % (resObj.iterTotalTime,)


  if buglev >= 5: print '\n===== incar parameters =====\n'

  # algo
  # PyLada: vasp/extract/base.py: algo()
  # OUTCAR: use the 1 occurance of:
  #   ALGO = Fast
  resObj.algo = getString( root, 'incar/i[@name=\'ALGO\']')
  if buglev >= 5: print 'algo: "%s"' % (resObj.algo,)

  ediff = getScalar( root, 'incar/i[@name=\'EDIFF\']', float)
  resObj.ediff = ediff
  if buglev >= 5: print 'ediff: %g' % (ediff,)

  # encut
  # PyLada: vasp/extract/base.py: encut()
  # OUTCAR: use the first occurance of:
  #   ENCUT  =  252.0 eV  18.52 Ry    4.30 a.u.   4.08  4.08 15.92*2*pi/ulx,y,z
  #   ENCUT = 252.0
  resObj.encut = getScalar( root, 'incar/i[@name=\'ENCUT\']', float)
  if buglev >= 5: print 'encut: %g' % (resObj.encut,)

  resObj.ibrion = getScalar( root, 'incar/i[@name=\'IBRION\']', int)
  if buglev >= 5: print 'ibrion: %g' % (resObj.ibrion,)

  resObj.isif = getScalar( root, 'incar/i[@name=\'ISIF\']', int)
  if buglev >= 5: print 'isif: %g' % (resObj.isif,)

  # ldauType
  # PyLada: vasp/extract/base.py: LDAUType()
  # OUTCAR: use the first occurance of:
  #   LDA+U is selected, type is set to LDAUTYPE =  2
  #   LDAUTYPE = 2
  #rawLdauType = getScalar( root, 'incar/v[@name=\'LDAUTYPE\']', int)
  #if rawLdauType == 1: resObj.ldauType = 'liechtenstein'
  #elif rawLdauType == 2: resObj.ldauType = 'dudarev'
  #else: throwerr('unknown rawLdauType: %d' % (rawLdauType,))
  #if buglev >= 5:
  #  print 'rawLdauType: %d  ldauType: %s' % (rawLdauType, resObj.ldauType,)

  resObj.systemName = getString( root, 'incar/i[@name=\'SYSTEM\']')
  if buglev >= 5: print 'systemName: "%s"' % (resObj.systemName,)



  if buglev >= 5: print '\n===== general parameters =====\n'

  resObj.generalName = getString(
    root, 'parameters/separator[@name=\'general\']/i[@name=\'SYSTEM\']')
  if buglev >= 5: print 'generalName: "%s"' % (resObj.generalName,)



  if buglev >= 5: print '\n===== electronic parameters =====\n'

  lst = root.findall('parameters/separator[@name=\'electronic\']')
  if len(lst) != 1: throwerr('electronic parameters not found')
  elecNode = lst[0]

  # ialgo
  # PyLada: use the 1 occurance of:
  #   Electronic relaxation 2 (details)
  #     IALGO  =     68    algorithm
  resObj.ialgo = getScalar( elecNode, 'i[@name=\'IALGO\']', int)
  if buglev >= 5: print 'ialgo: %d' % (resObj.ialgo,)

  # numBand = nbands
  # Caution: in some cases NBANDS != eigenMrr['eigene'].shape[2]
  # So we use the eigene dimension instead.
  # See further below.
  prmNumBand = getScalar( elecNode, 'i[@name=\'NBANDS\']', int)
  if buglev >= 5: print 'prmNumBand: %d' % (prmNumBand,)

  # numElectron = nelect
  # PyLada: vasp/extract/base.py: nelect()
  # OUTCAR: use the 1 occurance of:
  #     NELECT =      48.0000    total number of electrons
  resObj.numElectron = getScalar( elecNode, 'i[@name=\'NELECT\']', float)
  if buglev >= 5: print 'numElectron: %d' % (resObj.numElectron,)

  # icharg
  resObj.icharg = getScalar(
    elecNode,
    'separator[@name=\'electronic startup\']/i[@name=\'ICHARG\']',
    int)
  if buglev >= 5: print 'icharg: %g' % (resObj.icharg,)

  # numSpin == ispin
  resObj.numSpin = getScalar(
    elecNode, 'separator[@name=\'electronic spin\']/i[@name=\'ISPIN\']', int)
  if buglev >= 5: print 'numSpin: %g' % (resObj.numSpin,)


  if buglev >= 5: print '\n===== atom info =====\n'

  # atomTypeMrr = map containing array.  Example (some whitespace omitted):
  #   _dimLens: [2]
  #   _dimNames: ['type']
  #   _fieldNames: ['atomspertype' 'element' 'mass' 'valence' 'pseudopotential']
  #   _fieldTypes: ['i' 's' 'f' 'f' 's']
  #   atomspertype: [1 4]
  #   element: ['C ' 'Fe']
  #   mass: [ 12.011  55.847]
  #   valence: [ 4.  8.]
  #   pseudopotential: [' PAW_PBE C_s 06Sep2000 ' ' PAW_PBE Fe 06Sep2000 ']

  atomTypeMrr = getArrayByPath(
    buglev, root, 'atominfo/array[@name=\'atomtypes\']')
  resObj.typeNames    = atomTypeMrr['element']
  resObj.typeNums     = atomTypeMrr['atomspertype']
  resObj.typeMasses   = atomTypeMrr['mass']
  resObj.typeValences = atomTypeMrr['valence']
  resObj.typePseudos  = atomTypeMrr['pseudopotential']
  if buglev >= 5:
    print '\natomTypeMrr:'
    printMrr( atomTypeMrr)
    print 'typeNames: %s' % ( resObj.typeNames,)
    print 'typeNums: %s' % ( resObj.typeNums,)
    print 'typeMasses: %s' % ( resObj.typeMasses,)
    print 'typeValences: %s' % ( resObj.typeValences,)
    print 'typePseudos: %s' % ( resObj.typePseudos,)

  # totalValence = sum( count[i] * valence[i])
  # PyLada calls this valence.
  resObj.totalValence = np.dot( resObj.typeNums, resObj.typeValences)
  if buglev >= 5: print 'totalValence: %g' % (resObj.totalValence,)

  if resObj.numElectron != resObj.totalValence:
    throwerr('%g == numElectron != totalValence == %g' \
      % (resObj.numElectron, resObj.totalValence,))

  # atomMrr = map containing array.  Example:
  #   _dimLens: [5]
  #   _dimNames: ['ion']
  #   _fieldNames: ['element' 'atomtype']
  #   _fieldTypes: ['s' 'i']
  #   element: ['C ' 'Fe' 'Fe' 'Fe' 'Fe']
  #   atomtype: [1 2 2 2 2]

  atomMrr = getArrayByPath(
    buglev, root, 'atominfo/array[@name=\'atoms\']')
  if buglev >= 5:
    print '\natomMrr:'
    printMrr( atomMrr)

  resObj.atomNames = atomMrr['element']
  natom = len( resObj.atomNames)
  resObj.atomMasses = natom * [None]
  resObj.atomValences = natom * [None]
  resObj.atomPseudos = natom * [None]
  for ii in range( natom):
    ix = atomMrr['atomtype'][ii] - 1       # change to origin 0
    resObj.atomMasses[ii]   = resObj.typeMasses[ix]
    resObj.atomValences[ii] = resObj.typeValences[ix]
    resObj.atomPseudos[ii] = resObj.typePseudos[ix]
    if resObj.atomNames[ii] != resObj.typeNames[ix]:
      throwerr('name mismatch')
  if buglev >= 5:
    print 'atomNames: %s' % ( resObj.atomNames,)
    print 'atomMasses: %s' % ( resObj.atomMasses,)
    print 'atomValences: %s' % ( resObj.atomValences,)
    print 'atomPseudos: %s' % ( resObj.atomPseudos,)


  if buglev >= 5: print '\n===== initial structure =====\n'

  # Initial structure
  # PyLada: vasp/extract/base.py: initial_structure()
  # OUTCAR: uses the appended INITIAL STRUCTURE section.
  lst = root.findall(
    'structure[@name=\'initialpos\']/crystal/varray[@name=\'basis\']/v')
  if buglev >= 5: print 'len(lst) a:', len(lst)

  # initial_structure
  # POSCAR specifies each basis vector as one row.
  # So does vasprun.xml.
  # But PyLada's structure.cell is the transpose: each basis vec is a column.
  resObj.initialBasisMat = getRawArray(
    root,
    'structure[@name=\'initialpos\']/crystal/varray[@name=\'basis\']/v',
    3, 3, float)
  resObj.initialRecipBasisMat = getRawArray(
    root,
    'structure[@name=\'initialpos\']/crystal/varray[@name=\'rec_basis\']/v',
    3, 3, float)
  resObj.initialDirectPosMat = getRawArray(
    root,
    'structure[@name=\'initialpos\']/varray[@name=\'positions\']/v',
    0, 3, float)    # xxx nrow should be natom

  resObj.initialCartesianPosMat = np.dot(
    resObj.initialDirectPosMat, resObj.initialBasisMat)
  # xxx mult by scale factor?

  if buglev >= 5:
    print 'initialBasisMat:\n%s' % (repr(resObj.initialBasisMat),)
    print 'initialRecipBasisMat:\n%s' % (repr(resObj.initialRecipBasisMat),)
    print 'initialDirectPosMat:\n%s' % (repr(resObj.initialDirectPosMat),)
    print 'initialCartesianPosMat:\n%s' % (repr(resObj.initialCartesianPosMat),)
    print 'Check inverse: dot(basis,recip):\n%s' \
      % (repr(np.dot( resObj.initialBasisMat, resObj.initialRecipBasisMat)),)
    print 'Check inverse: dot(recip,basis):\n%s' \
      % (repr(np.dot( resObj.initialRecipBasisMat, resObj.initialBasisMat)),)



  if buglev >= 5: print '\n===== final structure =====\n'

  # structure == final pos
  # POSCAR specifies each basis vector as one row.
  # So does vasprun.xml.
  # But PyLada's structure.cell is the transpose: each basis vec is a column.
  # PyLada reads the catted CONTCAR.
  resObj.finalBasisMat = getRawArray(
    root,
    'structure[@name=\'finalpos\']/crystal/varray[@name=\'basis\']/v',
    3, 3, float)
  resObj.finalRecipBasisMat = getRawArray(
    root,
    'structure[@name=\'finalpos\']/crystal/varray[@name=\'rec_basis\']/v',
    3, 3, float)
  resObj.finalDirectPosMat = getRawArray(
    root,
    'structure[@name=\'finalpos\']/varray[@name=\'positions\']/v',
    0, 3, float)    # xxx nrow should be natom

  resObj.finalCartesianPosMat = np.dot(
    resObj.finalDirectPosMat, resObj.finalBasisMat)
  # xxx mult by scale factor?

  if buglev >= 5:
    print 'finalBasisMat:\n%s' % (repr(resObj.finalBasisMat),)
    print 'finalRecipBasisMat:\n%s' % (repr(resObj.finalRecipBasisMat),)
    print 'finalDirectPosMat:\n%s' % (repr(resObj.finalDirectPosMat),)
    print 'finalCartesianPosMat:\n%s' % (repr(resObj.finalCartesianPosMat),)
    print 'Check inverse: dot(basis,recip):\n%s' \
      % (repr(np.dot( resObj.finalBasisMat, resObj.finalRecipBasisMat)),)
    print 'Check inverse: dot(recip,basis):\n%s' \
      % (repr(np.dot( resObj.finalRecipBasisMat, resObj.finalBasisMat)),)



  if buglev >= 5: print '\n===== kpoints =====\n'

  # kpoint coordinates.
  # Not in PyLada?
  resObj.kpointRecipSpaceFracCoords = getRawArray(
    root, 'kpoints/varray[@name=\'kpointlist\']/v',
    0, 3, float)
  resObj.numKpoint = resObj.kpointRecipSpaceFracCoords.shape[0]

  resObj.kpointRecipSpaceCartCoords \
    = np.dot( resObj.kpointRecipSpaceFracCoords, resObj.initialRecipBasisMat)
  if buglev >= 5:
    print 'numKpoint: %g' % (resObj.numKpoint,)
    print 'kpointRecipSpaceFracCoords:\n%s' \
      % (repr(resObj.kpointRecipSpaceFracCoords),)
    print 'kpointRecipSpaceCartCoords:\n%s' \
      % (repr(resObj.kpointRecipSpaceCartCoords),)

  # This is what PyLada calls multiplicity.
  # The only diff is the scaling.
  #   sum( Pylada multiplicity) = numKpoint
  #   sum( our kpointWeights) = 1.0
  resObj.kpointWeights = getRawArray(
    root, 'kpoints/varray[@name=\'weights\']/v',
    0, 1, float)
  resObj.kpointWeights = resObj.kpointWeights[:,0]   # Only 1 col in 2d array
  if resObj.kpointWeights.shape[0] != resObj.numKpoint:
    throwerr('numKpoint mismatch')
  if buglev >= 5:
    print 'kpointWeights:\n%s' % (repr(resObj.kpointWeights),)
    print 'kpointWeights sum: %g' % (sum(resObj.kpointWeights),)



  if buglev >= 5: print '\n===== final volume and density =====\n'

  # volume, Angstrom^3
  volScale = 1.0
  resObj.finalVolumeCalc = abs( np.linalg.det(
    volScale * resObj.finalBasisMat))
  if buglev >= 5: print 'finalVolumeCalc: %g' % (resObj.finalVolumeCalc,)

  resObj.finalVolumeVasp = getScalar(
    root, 'structure[@name=\'finalpos\']/crystal/i[@name=\'volume\']', float)
  if buglev >= 5: print 'finalVolumeVasp: %g' % (resObj.finalVolumeVasp,)

  # reciprocal space volume, * (2*pi)**3
  invMat = np.linalg.inv( volScale * resObj.finalBasisMat)
  resObj.recVolumeCalc = abs( np.linalg.det( invMat)) * (2 * np.pi)**3
  if buglev >= 5:
    print 'recVolumeCalc: origMat:\n%s' \
      % (repr(volScale * resObj.finalBasisMat),)
    print 'recVolumeCalc: invMat:\n%s' % (repr(invMat),)
    print 'recVolumeCalc: det:\n%s' % (repr(np.linalg.det( invMat)),)
    print 'recVolumeCalc: %g' % (resObj.recVolumeCalc,)

  # Density
  # xxx better: get atomic weights from periodic table
  volCm = resObj.finalVolumeCalc / (1.e8)**3    # 10**8 Angstrom per cm
  totMass = np.dot( atomTypeMrr['atomspertype'], atomTypeMrr['mass'])
  totMassGm = totMass *  1.660538921e-24        #  1.660538921e-24 g / amu
  resObj.density = totMassGm / volCm
  if buglev >= 5:
    print 'volCm: %g' % (volCm,)
    print 'totMassGm: %g' % (totMassGm,)
    print 'density: %g' % (resObj.density,)


  if buglev >= 5: print '\n===== last calc forces =====\n'

  resObj.finalForceMat = getRawArray(
    root, 'calculation[last()]/varray[@name=\'forces\']/v',
    0, 3, float)
  if buglev >= 5: print 'finalForceMat:\n%s' % (repr(resObj.finalForceMat),)

  # Get stress
  resObj.finalStressMat = getRawArray(
    root, 'calculation[last()]/varray[@name=\'stress\']/v',
    3, 3, float)
  if buglev >= 5: print 'finalStressMat:\n%s' % (repr(resObj.finalStressMat),)

  # Calc pressure
  # xxx Caution: we do not include the non-diag terms in:
  #   VASP: force.F: FORCE_AND_STRESS: line 1410:
  #     PRESS=(TSIF(1,1)+TSIF(2,2)+TSIF(3,3))/3._q &
  #        &      -DYN%PSTRESS/(EVTOJ*1E22_q)*LATT_CUR%OMEGA
  diag = [resObj.finalStressMat[ii][ii] for ii in range(3)]
  resObj.finalPressure = sum( diag) / 3.0
  if buglev >= 5: print 'finalPressure: %g' % (resObj.finalPressure,)


  if buglev >= 5: print '\n===== eigenvalues and occupancies =====\n'

  # PyLada: eigenvalues
  eigenMrr = getArrayByPath(
    buglev, root, 'calculation[last()]/eigenvalues/array')
  if buglev >= 5:
    print '\neigenMrr beg =====:'
    printMrr( eigenMrr)
    print '\neigenMrr end =====:'
    for isp in range( resObj.numSpin):
      print '\neigenMrr: eigene[isp=%d][0]\n%s' \
        % (isp, repr(eigenMrr['eigene'][isp][0]),)
      print '\neigenMrr: occ[isp=%d][0]\n%s' \
        % (isp, repr(eigenMrr['occ'][isp][0]),)

  shp = eigenMrr['_dimLens']
  if shp[0] != resObj.numSpin: throwerr('numSpin mismatch')
  if shp[1] != resObj.numKpoint: throwerr('numKpoint mismatch')
  if shp[2] != prmNumBand:     # see caution at prmNumBand, above
    print('numBand mismatch: prm: %d  shape: %d  inXml: %s' \
      % (prmNumBand, shp[2], inXml,))
  resObj.numBand = shp[2]

  resObj.eigenMat = eigenMrr['eigene']
  # Caution: for non-magnetic, OUTCAR occMat = 2 while vasprun.xml = 1.
  # For magnetic, OUTCAR and vasprun.xml both have 1.
  resObj.occMat = eigenMrr['occ']
  if buglev >= 5:
    print 'resObj.eigenMat.shape: ', resObj.eigenMat.shape
    print 'resObj.occMat.shape: ', resObj.occMat.shape
  
  # Compare projected and standard eigenvalues
  getProjected = False
  if getProjected:
    for isp in range( resObj.numSpin):
      projEigenMrr = getArrayByPath(
        buglev, root, 'calculation[last()]/projected/eigenvalues/array')
      
      # eigs and projected eigs are identical
      eigs = resObj.eigenMrr['eigene'][isp]
      peigs = projEigenMrr['eigene'][isp]
      if buglev >= 5:
        print 'Compare iegs, peigs for isp: %d' % (isp,)
        print '  eigs.shape:  ', eigs.shape
        print '  peigs.shape: ', peigs.shape
        print '  eigs[0,:]: ', eigs[0,:]
        print '  peigs[0,:]: ', peigs[0,:]
        print '  Diff projeigs - eigs: max maxabs: %g' \
          % (max( map( max, abs(peigs - eigs))),)

      # occs and projected occs are identical
      occs = resObj.eigenMrr['occ'][isp]
      poccs = projEigenMrr['occ'][isp]
      if buglev >= 5:
        print 'Compare occs, poccs for isp: %d' % (isp,)
        print '  occs.shape:  ', occs.shape
        print '  poccs.shape: ', poccs.shape
        print '  occs[0,:]: ', occs[0,:]
        print '  poccs[0,:]: ', poccs[0,:]
        print '  Diff projoccs - occs: max maxabs: %g' \
          % (max( map( max, abs(poccs - occs))),)

  if buglev >= 5: print '\n===== misc junk =====\n'

  # PyLada: vasp/extract/base.py: is_gw()
  resObj.isGw = False
  if resObj.algo in  ['gw', 'gw0', 'chi', 'scgw', 'scgw0']: resObj.isGw = True
  if buglev >= 5: print 'isGw: %s' % (resObj.isGw,)

  # PyLada: vasp/extract/base.py: is_dft()
  resObj.isDft = not resObj.isGw
  if buglev >= 5: print 'isDft: %s' % (resObj.isDft,)

  # functional: comes from appended FUNCTIONAL.

  # success: look for final section
  #   General timing and accounting informations for this job:

  # xxx skip: Hubbard / NLEP

  

  if buglev >= 5: print '\n===== energy, efermi0 =====\n'

  resObj.finalEnergyWithout = getScalar(
    root, 'calculation[last()]/energy/i[@name=\'e_wo_entrp\']', float)

  # efermi0
  # PyLada uses an algorithm to compare the sum of occupancies
  # to the valence.
  # We get it from the xml file here.
  #   PyLada: 5.8574
  #   XML:    5.93253

  resObj.efermi0 = getScalar(
    root, 'calculation[last()]/dos/i[@name=\'efermi\']', float)
  if buglev >= 5: print 'efermi0: %g' % (resObj.efermi0,)


  if buglev >= 5: print '\n===== cbMin, vbMax, bandgap =====\n'

  # Find cbm = min of eigs >  efermi0
  # Find vbm = max of eigs <= efermi0

  cbms = resObj.numSpin * [np.inf]
  vbms = resObj.numSpin * [-np.inf]
  cbmKpis = resObj.numSpin * [None]
  vbmKpis = resObj.numSpin * [None]

  for isp in range( resObj.numSpin):
    eigs = resObj.eigenMat[isp]
    for ikp in range( resObj.numKpoint):
      for iband in range( resObj.numBand):
        val = eigs[ikp][iband]
        if val > resObj.efermi0:
          cbms[isp] = min( cbms[isp], val)
          cbmKpis[isp] = ikp
        if val <= resObj.efermi0:
          vbms[isp] = max( vbms[isp], val)
          vbmKpis[isp] = ikp

  cbms = map( float, cbms)     # change type from numpy.float64 to float
  vbms = map( float, vbms)     # change type from numpy.float64 to float

  resObj.cbms = cbms
  resObj.vbms = vbms
  resObj.cbmKpis = cbmKpis
  resObj.vbmKpis = vbmKpis
  resObj.cbMin = min( cbms)       # This is PyLada's cbm
  resObj.vbMax = max( vbms)       # This is PyLada's vbm

  resObj.bandgaps = [ (cbms[ii] - vbms[ii]) for ii in range( resObj.numSpin)]
  resObj.bandgapa = min( resObj.bandgaps)
  resObj.bandgap  = resObj.cbMin - resObj.vbMax   # This is PyLada version

  if buglev >= 5:
    print 'cbmKpis: %s  cbms: %s' % (cbmKpis, cbms,)
    print 'vbmKpis: %s  vbms: %s' % (vbmKpis, vbms,)
    print 'cbMin: %g' % (resObj.cbMin,)
    print 'vbMax: %g' % (resObj.vbMax,)
    print 'bandgaps: %s' % (resObj.bandgaps,)
    print 'bandgapa: %g' % (resObj.bandgapa,)
    print 'bandgap:  %g' % (resObj.bandgap,)



  # xxx
  # delta between cbmIndex, vbmIndex
  # print kpoints coords.  which is gamma, etc?
  # is any of frasier med exp?


  return






  ########################### STOP NOW ###############################









  print '\n'
  print '\ntesta:'
  lst = root.findall('kpoints/generation/v[@name=\'genvec2\']')
  amat = []
  for ele in lst:
    text = ele.text
    print '  ele.text: %s' % (text,)
    toks = text.split()
    vals = map( float, toks)
    amat.append( vals)
  print 'amat: %s' % (amat,)

  amat = np.array( amat, dtype=float)
  print 'amat:\n%s' % (amat,)

  vec = getVec( root, 'kpoints/generation/v[@name=\'genvec2\']', 0, 0, float)
  print 'vec:\n%s' % (vec,)

  amat = getRawArray( root, 'kpoints/generation/v', 0, 0, float)
  print 'amat:\n%s' % (amat,)

  calcNodes = root.findall('calculation')
  print '\nlen(calcNodes): %d' % (len(calcNodes,))

  # pairs: (itot, en_wo_entrp) for the energy of each scstep
  scstep_withouts = []
  # pairs: (itot, en_wo_entrp) for the last energy of each calculation step
  calcstep_withouts = []

  basisMats = []
  recipBasisMats = []
  posMats = []
  forceMats = []
  stressMats = []

  itot = 0     # index all scsteps, across calculations

  ncalc = len( calcNodes)
  for icalc in range( ncalc):
    cnode = calcNodes[icalc]
    forceMat = getRawArray( cnode, 'varray[@name=\'forces\']/v', 0, 0, float)
    print '\nforceMat for calcNodes[%d]:\n%s' % (icalc, forceMat,)
    scNodes = cnode.findall('scstep')
    print '    len(scNodes): %d' % (len(scNodes,))
    for isc in range(len(scNodes)):
      snode = scNodes[isc]
      ##print '#########:'; printNode(snode, 0, 10)
      sc_e_fr = getScalar( snode, 'energy/i[@name=\'e_fr_energy\']', float)
      sc_e_wo = getScalar( snode, 'energy/i[@name=\'e_wo_entrp\']', float)
      sc_e_0  = getScalar( snode, 'energy/i[@name=\'e_0_energy\']', float)
      print '    scNodes[%d]: sc_e_fr: %g  sc_e_wo: %g  sc_e_0: %g' \
        % (isc, sc_e_fr, sc_e_wo, sc_e_0,)

      scstep_withouts.append( (itot, sc_e_wo,))
      itot += 1

    # Structure for this calculation step
    strucNodes = cnode.findall('structure')
    if len(strucNodes) != 1: throwerr('calc structure not found')
    snode = strucNodes[0]
    basisMat = getRawArray(
      snode, 'crystal/varray[@name=\'basis\']/v', 3, 3, float)
    recipBasisMat = getRawArray(
      snode, 'crystal/varray[@name=\'rec_basis\']/v', 3, 3, float)
    # xxx should be nrow = num atoms
    posMat = getRawArray(
      snode, 'varray[@name=\'positions\']/v', 0, 3, float)
    print '  Calc final: basisMat:\n%s' % (basisMat,)
    print '  Calc final: recipBasisMat:\n%s' % (recipBasisMat,)
    print '  Calc final: posMat:\n%s' % (posMat,)
    basisMats.append( basisMat)
    recipBasisMats.append( recipBasisMat)
    posMats.append( posMat)

    # Forces for this calculation step
    forceNodes = cnode.findall('varray[@name=\'forces\']')
    if len(forceNodes) != 1: throwerr('calc forces not found')
    forceMat = getRawArray( forceNodes[0], 'v', 0, 3, float)
    print '  Calc final: forceMat:\n%s' % (forceMat,)
    forceMats.append( forceMat)

    # Stress for this calculation step
    stressNodes = cnode.findall('varray[@name=\'stress\']')
    if len(stressNodes) != 1: throwerr('calc stresses not found')
    stressMat = getRawArray( stressNodes[0], 'v', 3, 3, float)
    print '  Calc final: stressMat:\n%s' % (stressMat,)
    stressMats.append( stressMat)

    # Final energy for this calculation step
    enNodes = cnode.findall('energy')
    if len(enNodes) != 1: throwerr('calc energy not found')
    enode = enNodes[0]
    c_e_fr = getScalar( enode, 'i[@name=\'e_fr_energy\']', float)
    c_e_wo = getScalar( enode, 'i[@name=\'e_wo_entrp\']', float)
    c_e_0  = getScalar( enode, 'i[@name=\'e_0_energy\']', float)
    print '  Calc final: c_e_fr: %g  c_e_wo: %g  c_e_0: %g' \
      % (c_e_fr, c_e_wo, c_e_0,)
    calcstep_withouts.append( (itot - 1, c_e_wo,))

  print ''
  print 'scstep_withouts: %s' % (scstep_withouts,)
  print ''
  print 'calcstep_withouts: %s' % (calcstep_withouts,)

  scmat = np.array( scstep_withouts, dtype=float)
  print ''
  print 'scmat:\n%s' % (scmat,)

  calcmat = np.array( calcstep_withouts, dtype=float)
  print ''
  print 'calcmat:\n%s' % (calcmat,)


  print ''
  print 'Investigate DOS'
  icals = len(calcNodes) - 1
  cnode = calcNodes[icalc]
  setNodes = cnode.findall('dos/total/array/set/set[@comment=\'spin 1\']')
  print '    len(total setNodes): %d' % (len(setNodes),)
  print '    setNodes[0]: %s' % (setNodes[0],)
  if len(setNodes) != 1: throwerr('dos/total not found')
  dosTotalMat = getRawArray( setNodes[0], 'r', 0, 0, float)
  print ''
  print 'type(dosTotalMat): ', type(dosTotalMat)
  print 'dosTotalMat.shape: ', dosTotalMat.shape
  print ''
  print 'dosTotalMat:\n%s' % (dosTotalMat,)

  dosPartialMats = []
  partialSetNodes = cnode.findall('dos/partial/array/set')
  print '    len(partialSetNodes): %d' % (len(partialSetNodes),)
  if len(partialSetNodes) != 1: throwerr('dos/partial not found')
  partialSet = partialSetNodes[0]

  ionNodes = partialSet.findall('set')
  print '    len(ionNodes): %d' % (len(ionNodes),)
  # xxx should be nrow = num atoms
  for ii in range(len(ionNodes)):
    dosPartialMat = getRawArray(
      ionNodes[ii], 'set[@comment=\'spin 1\']/r', 0, 0, float)
    print ''
    print 'dosPartialMat %d:' % (ii,)
    print 'type(dosPartialMat): ', type(dosPartialMat)
    print 'dosPartialMat.shape: ', dosPartialMat.shape
    print ''
    print 'dosPartialMat:\n%s' % (dosPartialMat,)
    dosPartialMats.append( dosPartialMat)

  print 'len(dosPartialMats): %d' % (len(dosPartialMats),)




  print '\nbasisMats:  len: %d' % (len(basisMats),)
  for mat in basisMats: print '%s' % (mat,)

  print '\nrecipBasisMats:  len: %d' % (len(recipBasisMats),)
  for mat in recipBasisMats: print '%s' % (mat,)

  print '\nposMats:  len: %d' % (len(posMats),)
  for mat in posMats: print '%s' % (mat,)

  print '\nforceMats:  len: %d' % (len(forceMats),)
  for mat in forceMats: print '%s' % (mat,)

  print '\nstressMats:  len: %d' % (len(stressMats),)
  for mat in stressMats: print '%s' % (mat,)

  basisDeltas = calcMatDeltas( basisMats)
  recipBasisDeltas = calcMatDeltas( recipBasisMats)
  posDeltas = calcMatDeltas( posMats)
  forceDeltas = calcMatDeltas( forceMats)
  stressDeltas = calcMatDeltas( stressMats)

  print 'basisDeltas: %s' % ( basisDeltas,)
  print 'recipBasisDeltas: %s' % ( recipBasisDeltas,)
  print 'posDeltas: %s' % ( posDeltas,)
  print 'forceDeltas: %s' % ( forceDeltas,)
  print 'stressDeltas: %s' % ( stressDeltas,)




  import matplotlib
  matplotlib.use('tkagg')
  import matplotlib.pyplot as plt

  fig, axes = plt.subplots( 1, 1)
  ##ax00 = axes[0,0]
  ax00 = axes
  ax00.plot( dosTotalMat[:,0], dosTotalMat[:,1], color='r', linestyle='-',
    marker=None)
  ax00.set_xlabel('Energy, eV')
  ax00.set_ylabel('Number of states per unit cell')
  ax00.set_title('Density of states')
  ax00.xaxis.grid(color='lightblue', linestyle='solid')
  ax00.yaxis.grid(color='lightblue', linestyle='solid')
  #plt.show()


#fig, ax = plt.subplots()
#
#ax.plot( scmat[:,0], scmat[:,1], 'b-')
#ax.plot( calcmat[:,0], calcmat[:,1], 'bo')
#ax.set_ylim( calcmat[-1,1] - 5, calcmat[-1,1] + 5)
#ax.xaxis.grid(color='lightblue', linestyle='solid')
#ax.yaxis.grid(color='lightblue', linestyle='solid')
#
#savefig('tempa.png', dpi=100, orientation='landscape', papertype='letter')
#
#plt.show()


  tnodes = root.findall('calculation[last()]')
  print '########## tnodes    a: %s' % (tnodes,)
  print '########## tnodes[0] a: %s' % (tnodes[0],)
  printNode( tnodes[0], 0, 1)

  tnodes = root.findall('calculation[last()]/eigenvalues')
  print '########## tnodes    b: %s' % (tnodes,)
  print '########## tnodes[0] b: %s' % (tnodes[0],)
  printNode( tnodes[0], 0, 1)

  tnodes = root.findall('calculation[last()]/eigenvalues/array')
  print '########## tnodes    c: %s' % (tnodes,)
  print '########## tnodes[0] c: %s' % (tnodes[0],)
  printNode( tnodes[0], 0, 1)

  res = getArrayByPath(
    buglev, root, 'calculation[last()]/eigenvalues/array')
  print '\ncalculation[last()]/eigenvalues:\n%s' % (res,)

  print '\n'

#====================================================================


def printNode( node, curLev, maxLev):
  if curLev <= maxLev:
    if node.tail == None: tail = 'None'
    else: tail = '"%s"' % (node.tail.strip(),)

    if node.text == None: text = 'None'
    else: text = '"%s"' % (node.text.strip(),)

    print '%stag: %s  attrib: %s  tail: %s  text: %s' \
      % (curLev * '  ', node.tag, node.attrib, tail, text,)

    for kid in node:
      printNode( kid, curLev + 1, maxLev)

#====================================================================

def parseText( path, nmin, nmax, dtype, text):
  if buglev >= 1: print '  parseText: ele.text: %s' % (text,)
  toks = text.split()
  ntok = len( toks)
  if ntok < nmin:
    throwerr('ntok < nmin for path: "%s"  text: "%s"' % (path, text,))
  if nmax > 0 and ntok > nmax:
    throwerr('ntok > nmax for path: "%s"  text: "%s"' % (path, text,))

  vals = ntok * [None]
  for ii in range(ntok):
    tok = toks[ii]
    if dtype == int:
      try: val = int( tok)
      except ValueError, exc:
        throwerr('invalid int in path: "%s"  text: "%s"' % (path, text,))
    elif dtype == float:
      try: val = float( tok)
      except ValueError, exc:
        throwerr('invalid float in path: "%s"  text: "%s"' % (path, text,))
    elif dtype == str: val = tok
    else: throwerr('unknown dtype for path: "%s"' % (path,))
    vals[ii] = val
  return vals
#====================================================================

def getVec( root, path, nmin, nmax, dtype):
  text = getString( root, path)
  vals = parseText( path, nmin, nmax, dtype, text)
  return vals

#====================================================================

# Return stripped string

def getString( root, path):
  lst = root.findall( path)
  if len(lst) == 0:
    throwerr('path not found: "%s"' % (path,))
  if len(lst) > 1:
    throwerr('multiple matches for path: "%s"' % (path,))
  ele = lst[0]
  text = ele.text
  return text.strip()

#====================================================================

def getScalar( root, path, dtype):

  lst = getVec( root, path, 1, 1, dtype)
  return lst[0]

#====================================================================

def getRawArray( root, path, nrow, ncol, dtype):
  lst = root.findall( path)
  nlst = len( lst)
  if nlst == 0: throwerr('path not found: "%s"' % (path,))
  if nrow > 0 and nlst != nrow:
    throwerr('nrow mismatch for path: "%s".  expected: %d  found: %d' \
      % (path, nrow, nlst,))

  rows = []
  for ii in range(nlst):

    ele = lst[ii]
    text = ele.text
    vals = parseText( path, 0, 0, dtype, text)
    if len(rows) == 0: ncolActual = len( vals)
    if len(vals) != ncolActual:
      throwerr('irregular array for path: "%s"' % (path,))
    if ncol > 0 and ncolActual != ncol:
      throwerr('ncol mismatch path: "%s"' % (path,))
    rows.append( vals)

  if dtype == int:
    amat = np.array( rows, dtype=int)
  elif dtype == float:
    amat = np.array( rows, dtype=float)
  else: throwerr('unknown dtype for path: "%s"' % (path,))

  return amat


#====================================================================

def getArrayByPath( buglev, baseNode, path):
  arrNodes = baseNode.findall( path)
  if len(arrNodes) != 1: throwerr('path not found')
  res = getArrayByNode( buglev, arrNodes[0])
  return res

#====================================================================


# Returns Mrr == map containing array, like:
#   atomMrr:
#     _dimLens: [6]
#     _dimNames: ['ion']
#     _fieldNames: ['element', 'atomtype']
#     _fieldTypes: ['s', 'i']
#     element: ['Mo' 'Mo' 'S' 'S' 'S' 'S']
#     atomtype: [1 1 2 2 2 2]

def getArrayByNode( buglev, arrNode):

  dimNodes = arrNode.findall('dimension')
  ndim = len( dimNodes)
  if ndim == 0: throwerr('no dimensions found')
  dimNames = [nd.text for nd in dimNodes]
  dimNames.reverse()         # dimNames are in reverse order in xml
  dimNames = np.array( dimNames, dtype=str)
  dimLens = np.zeros( [ndim], dtype=int)

  fieldNodes = arrNode.findall('field')
  nfield = len( fieldNodes)
  if nfield == 0: throwerr('no fields found')
  fieldNames = [nd.text for nd in fieldNodes]
  fieldNames = np.array( fieldNames, dtype=str)

  # We set fieldTypes[ifield] to max( all found types for ifield)
  # Types are: 0:int, 1:float, 2:string
  fieldTypes = nfield * [0]

  setNodes = arrNode.findall('set')
  if len(setNodes) != 1: throwerr('wrong len for primary set')
  setNode = setNodes[0]
  resList = nfield * [None]
  for ifield in range( nfield):
    amat = getArraySub(
      buglev,
      setNode,
      ifield,
      fieldTypes,
      0,            # idim
      dimLens)

    # Convert all elements of each field ifield to fieldTypes[ifield].
    if   fieldTypes[ifield] == 0: amat = np.array( amat, dtype=int)
    elif fieldTypes[ifield] == 1: amat = np.array( amat, dtype=float)
    elif fieldTypes[ifield] == 2: amat = np.array( amat, dtype=str)
    else: throwerr('unknown fieldType')

    resList[ifield] = amat

  # Convert fieldTypes from 0,1,2 to 'i', 'f', 's'
  fldMap = { 0:'i', 1:'f', 2:'s'}
  fieldTypeStgs = map( lambda x: fldMap[x], fieldTypes)
  fieldTypeStgs = np.array( fieldTypeStgs, dtype=str)

  resMap = {
    '_dimNames': dimNames,
    '_dimLens': dimLens,
    '_fieldNames': fieldNames,
    '_fieldTypes': fieldTypeStgs,
  }
  for ii in range(len(fieldNames)):
    ar = np.array( resList[ii])
    if not all(ar.shape == np.array(dimLens)): throwerr('dimLens mismatch')
    resMap[fieldNames[ii]] = ar

  return resMap

#====================================================================

def convertTypes( tp, vec):
  if isinstance( vec[0], str):
    for ii in range(len(vec)):
      'print '#############' type val bef:', type(vec[ii]), '  aft: ', type(tp(vec[ii]))
      vec[ii] = tp( vec[ii])
  elif isinstance( vec[0], list):
    for subVec in vec:
      convertTypes( tp, subVec)             # recursion
  else: throwerr('unknown array structure')

#====================================================================


def getArraySub(
  buglev,
  setNode,
  ifield,
  fieldTypes,
  idim,
  dimLens):

  nfield = len(fieldTypes)
  ndim = len(dimLens)

  # If we're at the last dimension, decode the element values.
  if idim == ndim - 1:
    # Try long form:
    #   <set>
    #     <rc>
    #       <c>2</c>
    #       <c>Mo</c>
    rcNodes = setNode.findall('rc')     # long form: <rc> <c>

    # Try short form:
    #   <set comment='spin 1'>
    #     <set comment='kpoint 1'>
    #       <r>-30.3711 1.0000</r>
    #       <r>-30.3709 1.0000</r>
    rNodes = setNode.findall('r')       # short form: <r>

    nval = max( len( rcNodes), len( rNodes))
    if dimLens[idim] == 0: dimLens[idim] = nval
    if nval != dimLens[idim]: throwerr('irregular array')
    resVec = nval * [None]

    if len(rcNodes) > 0:                # long form: <rc> <c>
      for ival in range( nval):
        cNodes = rcNodes[ival].findall('c')
        if len(cNodes) != nfield: throwerr('wrong num fields')
        stg = cNodes[ifield].text
        resVec[ival] = stg

    elif len(rNodes) > 0:               # short form: <r>
      for ival in range( nval):
        txt = rNodes[ival].text
        toks = txt.split()
        if len(toks) != nfield: throwerr('wrong num fields')
        resVec[ival] = toks[ifield]

    else: throwerr('unknown array structure')

    # Strip all strings.
    # Set fieldTypes[ifield] to max( current type, all found types)
    # Types are: 0:int, 1:float, 2:string
    for ival in range( nval):
      resVec[ival] = resVec[ival].strip()
      stg = resVec[ival]
      ftype = 2            # assume worst case: string
      try:
        float( stg)
        ftype = 1
      except ValueError: pass
      try:
        int( stg)
        ftype = 0
      except ValueError: pass
      fieldTypes[ifield] = max( fieldTypes[ifield], ftype)


  else:    # else idim < ndim - 1.  Recursion.
    setNodes = setNode.findall('set')
    nset = len( setNodes)
    if dimLens[idim] == 0: dimLens[idim] = nset
    if nset != dimLens[idim]: throwerr('irregular array')
    resVec = nset * [None]
    for iset in range(nset):
      resVec[iset] = getArraySub(          # recursion
        buglev,
        setNodes[iset],
        ifield,
        fieldTypes,
        idim + 1,
        dimLens)

  return resVec
 

#====================================================================

def maxAbsDiff( mata, matb):
  (nrow,ncol) = mata.shape
  if matb.shape != mata.shape: throwerr('maxAbsDiff: shape mismatch')
  diffMat =  abs( matb) - abs( mata)
  res = max( map( max, diffMat))
  return res

#====================================================================

def calcMatDeltas( mats):
  nmat = len( mats)
  deltas = []
  for ii in range( 1, nmat):
    delta = maxAbsDiff( mats[ii-1], mats[ii])
    deltas.append( delta)
  return deltas

#====================================================================

def printMrr( vmap):
  keys = vmap.keys()
  keys.sort()
  for key in keys:
    if key.startswith('_'):
      val = vmap[key]
      print '  %s: %s' % (key, val,)
  for key in vmap['_fieldNames']:
    val = vmap[key]
    print '  %s: %s' % (key, val,)
  print ''

#====================================================================

def throwerr( msg):
  print msg
  print >> sys.stderr, msg
  raise Exception( msg)

#====================================================================

if __name__ == '__main__': main()

#====================================================================
